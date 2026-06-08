import asyncio
import os
import socket
import sys
import traceback
import threading
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from utils.network_tools import get_default_interface_ipv4
from utils.packet_templates import ClientHelloMaker
from fake_tcp import FakeInjectiveConnection, FakeTcpInjector

def get_exe_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(get_exe_dir(), 'config.json')
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    logging.error(f"Configuration file not found at: {config_path}")
    sys.exit(1)
except json.JSONDecodeError:
    logging.error(f"Error decoding JSON from configuration file: {config_path}")
    sys.exit(1)

LISTEN_HOST = config.get("LISTEN_HOST", "127.0.0.1")
LISTEN_PORT = config.get("LISTEN_PORT", 40443)
CONNECT_IPS = config.get("CONNECT_IPS", ["188.114.98.0"])
FAKE_SNIS_LIST = config.get("FAKE_SNIS", ["auth.vercel.com"])
CONNECT_PORT = config.get("CONNECT_PORT", 443)
INTERFACE_IPV4_CONFIG = config.get("INTERFACE_IPV4", None)
DATA_MODE = config.get("DATA_MODE", "tls")
BYPASS_METHOD = config.get("BYPASS_METHOD", "wrong_seq")

if not CONNECT_IPS or not FAKE_SNIS_LIST:
    logging.error("CONNECT_IPS and FAKE_SNIS must be provided in config.json")
    sys.exit(1)

active_connections: dict[tuple, FakeInjectiveConnection] = {}

# Global variables for the selected best route
BEST_IP = None
BEST_SNI_BYTES = None
BEST_INTERFACE_IPV4 = None

async def test_route(ip: str, sni: bytes, loop, conn_port: int, interface_ipv4_config: str | None, bypass_method: str) -> tuple[float, bool, int]:
    score = float('inf')
    success = False
    max_attempts = 2
    min_rtt = float('inf')
    timeouts = 0

    if not isinstance(ip, str):
        logging.error(f"Invalid IP address type: {type(ip)}. Expected str.")
        return score, False, timeouts

    logging.debug(f"Testing route: IP={ip}, SNI={sni.decode(errors='ignore')}")

    for attempt in range(max_attempts):
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.setblocking(False)

            interface_for_bind = interface_ipv4_config
            if interface_for_bind is None:
                detected_interface = get_default_interface_ipv4(ip)
                if detected_interface and isinstance(detected_interface, str):
                    interface_for_bind = detected_interface
                else:
                    interface_for_bind = "0.0.0.0"

            if not isinstance(interface_for_bind, (str, bytes)):
                logging.error(f"Invalid interface address type for binding: {type(interface_for_bind)}")
                raise TypeError("Interface address must be a string or bytes")

            bind_address = (interface_for_bind, 0) if interface_for_bind and interface_for_bind != "0.0.0.0" else (0, 0)
            test_sock.bind(bind_address)

            start_time = loop.time()
            await asyncio.wait_for(loop.sock_connect(test_sock, (ip, conn_port)), timeout=5.0)
            connection_time = loop.time() - start_time

            fake_data = ClientHelloMaker.get_client_hello_with(os.urandom(32), os.urandom(32), sni, os.urandom(32))
            await loop.sock_sendall(test_sock, fake_data)
            await asyncio.sleep(0.5)

            try:
                await loop.sock_sendall(test_sock, b'\x01')
                success = True
                min_rtt = min(min_rtt, connection_time)
                break
            except (ConnectionResetError, OSError):
                timeouts += 1
                logging.debug(f"Route {ip}:{sni.decode(errors='ignore')} - Attempt {attempt+1}/{max_attempts}: Failed after handshake.")
            finally:
                test_sock.close()

        except asyncio.TimeoutError:
            timeouts += 1
        except (ConnectionRefusedError, OSError) as e:
            logging.debug(f"Route {ip}:{sni.decode(errors='ignore')} - Attempt {attempt+1}/{max_attempts}: Error: {e}")
            timeouts += 1
        except TypeError as e:
            logging.error(f"TypeError testing route {ip}:{sni.decode(errors='ignore')}: {e}")
            timeouts += 1
        except Exception as e:
            logging.error(f"Unexpected error testing route {ip}:{sni.decode(errors='ignore')}: {e}")
            timeouts += 1

    if success:
        score = min_rtt
    else:
        score = float('inf')

    logging.debug(f"Route {ip}:{sni.decode(errors='ignore')} - Score: {score:.2f}, Success: {success}, Timeouts: {timeouts}")
    return score, success, timeouts


async def select_best_route(loop):
    global BEST_IP, BEST_SNI_BYTES, BEST_INTERFACE_IPV4

    logging.info(f"Starting route testing with {len(CONNECT_IPS)} IPs and {len(FAKE_SNIS_LIST)} SNIs.")

    route_tasks = []
    for ip in CONNECT_IPS:
        for sni_str in FAKE_SNIS_LIST:
            sni_bytes = sni_str.encode()
            route_tasks.append(
                test_route(ip, sni_bytes, loop, CONNECT_PORT, INTERFACE_IPV4_CONFIG, BYPASS_METHOD)
            )

    results = await asyncio.gather(*route_tasks, return_exceptions=True)

    best_score = float('inf')
    best_ip = None
    best_sni_bytes = None

    route_index = 0
    for ip in CONNECT_IPS:
        for sni_str in FAKE_SNIS_LIST:
            sni_bytes = sni_str.encode()
            result = results[route_index]
            route_index += 1

            if isinstance(result, tuple) and len(result) == 3:
                score, success, timeouts = result
                if success and score < best_score:
                    best_score = score
                    best_ip = ip
                    best_sni_bytes = sni_bytes
                    selected_route_details = f"IP={ip}, SNI={sni_str}, Score={score:.2f}"

    if not best_ip or not best_sni_bytes:
        logging.error("Failed to find any working route. Exiting.")
        sys.exit(1)

    BEST_IP = best_ip
    BEST_SNI_BYTES = best_sni_bytes
    logging.info(f"Best route selected: {selected_route_details}")

    # Determine the interface IP for binding
    BEST_INTERFACE_IPV4 = INTERFACE_IPV4_CONFIG
    if BEST_INTERFACE_IPV4 is None:
        detected = get_default_interface_ipv4(BEST_IP)
        if detected and isinstance(detected, str):
            BEST_INTERFACE_IPV4 = detected
        else:
            BEST_INTERFACE_IPV4 = "0.0.0.0"

    if not isinstance(BEST_INTERFACE_IPV4, (str, bytes)):
        logging.error(f"Invalid interface address type: {type(BEST_INTERFACE_IPV4)}")
        sys.exit(1)


async def relay_main_loop(sock_1: socket.socket, sock_2: socket.socket, first_prefix_data: bytes, connection_id: tuple, loop):
    try:
        while True:
            data = await loop.sock_recv(sock_1, 65575)
            if not data:
                logging.debug(f"Connection {connection_id}: EOF. Closing.")
                break

            if first_prefix_data:
                data = first_prefix_data + data
                first_prefix_data = b""

            await loop.sock_sendall(sock_2, data)

    except asyncio.CancelledError:
        pass
    except ConnectionResetError:
        logging.debug(f"Connection {connection_id}: Connection reset.")
    except OSError as e:
        if e.errno in (10054, 10053, 10038, 121, 10058, 10060) or getattr(e, 'winerror', None) in (121, 10060, 10054, 10053, 10038, 10058):
            logging.debug(f"Connection {connection_id}: Connection closed (OSError/WinError).")
        else:
            logging.error(f"Connection {connection_id}: OS Error: {e}")
    except Exception as e:
        logging.error(f"Connection {connection_id}: Unexpected error: {e}")


async def handle(incoming_sock: socket.socket, incoming_remote_addr: tuple):
    global BEST_IP, BEST_SNI_BYTES, BEST_INTERFACE_IPV4

    loop = asyncio.get_running_loop()
    conn_id = None

    try:
        outgoing_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        outgoing_sock.setblocking(False)
        outgoing_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        outgoing_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 11)
        outgoing_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 2)
        outgoing_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

        try:
            bind_address = (BEST_INTERFACE_IPV4, 0) if BEST_INTERFACE_IPV4 and BEST_INTERFACE_IPV4 != "0.0.0.0" else (0, 0)
            outgoing_sock.bind(bind_address)
            src_port = outgoing_sock.getsockname()[1]
            conn_id = (BEST_INTERFACE_IPV4 if BEST_INTERFACE_IPV4 else "0.0.0.0", src_port, BEST_IP, CONNECT_PORT)
            logging.debug(f"Connection {conn_id}: Binding to {BEST_INTERFACE_IPV4}")
        except OSError as e:
            logging.error(f"Connection: Failed to bind: {e}")
            incoming_sock.close()
            outgoing_sock.close()
            return

        if DATA_MODE == "tls":
            fake_data = ClientHelloMaker.get_client_hello_with(os.urandom(32), os.urandom(32), BEST_SNI_BYTES, os.urandom(32))
        else:
            logging.error(f"Unsupported DATA_MODE: {DATA_MODE}")
            incoming_sock.close()
            outgoing_sock.close()
            return

        fake_injective_conn = FakeInjectiveConnection(
            outgoing_sock, BEST_INTERFACE_IPV4 if BEST_INTERFACE_IPV4 else "0.0.0.0", BEST_IP, src_port, CONNECT_PORT,
            fake_data, BYPASS_METHOD, incoming_sock
        )
        active_connections[conn_id] = fake_injective_conn

        try:
            await loop.sock_connect(outgoing_sock, (BEST_IP, CONNECT_PORT))
            logging.debug(f"Connection {conn_id}: Connected to {BEST_IP}:{CONNECT_PORT}")
        except Exception as e:
            logging.error(f"Connection {conn_id}: Failed to connect: {e}")
            if conn_id in active_connections:
                del active_connections[conn_id]
            incoming_sock.close()
            outgoing_sock.close()
            return

        if BYPASS_METHOD in ("wrong_seq", "wrong_ttl"):
            try:
                await asyncio.wait_for(fake_injective_conn.t2a_event.wait(), timeout=5.0)
                if fake_injective_conn.t2a_msg == "unexpected_close":
                    raise ValueError("unexpected close during bypass")
                elif fake_injective_conn.t2a_msg != "fake_data_ack_recv":
                    raise ValueError(f"unexpected bypass message: {fake_injective_conn.t2a_msg}")
                logging.debug(f"Connection {conn_id}: Bypass successful.")
            except Exception:
                if conn_id in active_connections:
                    del active_connections[conn_id]
                incoming_sock.close()
                outgoing_sock.close()
                return
        else:
            logging.error(f"Unknown bypass method: {BYPASS_METHOD}")
            if conn_id in active_connections:
                del active_connections[conn_id]
            incoming_sock.close()
            outgoing_sock.close()
            return

        if conn_id in active_connections:
            del active_connections[conn_id]

        peer_task_1 = asyncio.create_task(
            relay_main_loop(outgoing_sock, incoming_sock, b"", conn_id, loop)
        )
        peer_task_2 = asyncio.create_task(
            relay_main_loop(incoming_sock, outgoing_sock, b"", conn_id, loop)
        )
        
        done, pending = await asyncio.wait(
            [peer_task_1, peer_task_2],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for task in pending:
            task.cancel()
            
        if pending:
            await asyncio.wait(pending)

    except Exception as e:
        logging.exception(f"Connection {conn_id}: Error in handle.")
    finally:
        if 'outgoing_sock' in locals() and outgoing_sock.fileno() != -1:
            try: 
                outgoing_sock.close() 
            except Exception: 
                pass
        if incoming_sock and incoming_sock.fileno() != -1:
            try: 
                incoming_sock.close() 
            except Exception: 
                pass
        logging.debug(f"Connection {conn_id}: Closed.")


async def main():
    global BEST_IP, BEST_SNI_BYTES, BEST_INTERFACE_IPV4

    loop = asyncio.get_running_loop()

    # Select the best route once at startup
    await select_best_route(loop)
    logging.info(f"Using route: IP={BEST_IP}, SNI={BEST_SNI_BYTES.decode(errors='ignore')}, Interface={BEST_INTERFACE_IPV4}")

    w_filter = f"tcp and ((ip.SrcAddr == {BEST_INTERFACE_IPV4} and ip.DstAddr == {BEST_IP}) or (ip.SrcAddr == {BEST_IP} and ip.DstAddr == {BEST_INTERFACE_IPV4}))"
    fake_tcp_injector = FakeTcpInjector(w_filter, active_connections)
    threading.Thread(target=fake_tcp_injector.run, args=(), daemon=True).start()
    logging.info("Packet injector started.")

    mother_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    mother_sock.setblocking(False)
    mother_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        mother_sock.bind((LISTEN_HOST, LISTEN_PORT))
        mother_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        mother_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 11)
        mother_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 2)
        mother_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        mother_sock.listen()
        logging.info(f"Server listening on {LISTEN_HOST}:{LISTEN_PORT}")
    except OSError as e:
        logging.error(f"Failed to bind to {LISTEN_HOST}:{LISTEN_PORT}: {e}")
        sys.exit(1)

    while True:
        try:
            incoming_sock, addr = await loop.sock_accept(mother_sock)
            incoming_sock.setblocking(False)
            incoming_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            incoming_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 11)
            incoming_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 2)
            incoming_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
            task = asyncio.create_task(handle(incoming_sock, addr))
            task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
        except OSError as e:
            if e.winerror == 64:
                continue
            logging.error(f"Error accepting connection: {e}")
        except Exception as e:
            logging.error(f"Unexpected error during connection acceptance: {e}")


if __name__ == "__main__":
    logging.info("Starting SNI-Spoofing proxy...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user.")
    except Exception as e:
        logging.exception("An unhandled exception occurred.")
