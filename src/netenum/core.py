"""Network enumeration module for efficient IP address generation from CIDR ranges.

This module provides tools for enumerating IP addresses from multiple CIDR ranges
efficiently, without expanding entire ranges in memory. It supports both IPv4 and
IPv6 addresses and provides both synchronous and asynchronous interfaces.
"""

import asyncio
import ipaddress
import logging
import math
from collections import deque
from typing import AsyncIterator, Iterator, List, Union

# Configure logging
logger = logging.getLogger(__name__)

IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


def determine_partition_size(network: IPNetwork) -> int:
    """
    Determine an efficient partition size based on network size.

    The function uses a logarithmic scaling approach to determine partition sizes:
    - For IPv4: Partitions scale from /24 (256 addresses) up to /22 (1024 addresses)
    - For IPv6: Partitions scale from /112 (65536 addresses) up to /108 (~1M addresses)

    Args:
        network: An IPv4Network or IPv6Network object to analyze

    Returns:
        int: The number of addresses to include in each partition

    Examples:
        >>> net = ipaddress.ip_network('192.168.0.0/24')
        >>> determine_partition_size(net)
        256
        >>> net = ipaddress.ip_network('10.0.0.0/8')
        >>> determine_partition_size(net)
        1024
    """
    num_addresses = network.num_addresses
    logger.debug(f"Determining partition size for network {network} " f"with {num_addresses} addresses")

    if isinstance(network, ipaddress.IPv4Network):
        if num_addresses <= 256:
            logger.debug(f"Using exact size {num_addresses} for small IPv4 network")
            return int(num_addresses)
        partition_bits = min(max(8, math.floor(math.log2(float(num_addresses)) - 8)), 10)
    else:
        if num_addresses <= 65536:
            logger.debug(f"Using exact size {num_addresses} for small IPv6 network")
            return int(num_addresses)
        partition_bits = min(max(16, math.floor(math.log2(float(num_addresses)) - 16)), 20)

    size = int(2**partition_bits)
    logger.debug(f"Calculated partition size: {size} addresses")
    return size


class NetworkEnumerator:
    """
    A class for efficient enumeration of IP addresses across multiple CIDR ranges.

    This class provides both synchronous and asynchronous iteration over IP addresses
    from multiple networks. It uses a partitioning strategy to avoid expanding entire
    ranges in memory, making it suitable for very large networks.

    The enumeration stripes across all networks, yielding addresses from each network
    in turn to ensure fair distribution when multiple networks are provided.

    Attributes:
        networks: List of tuples containing (generator, address_class) pairs for each
            network

    Examples:
        >>> enumerator = NetworkEnumerator(['192.168.0.0/24', '10.0.0.0/8'])
        >>> for addr in enumerator:
        ...     print(addr)
        192.168.0.0
        10.0.0.0
        192.168.0.1
        10.0.0.1
        # ... and so on
    """

    def __init__(self, cidrs: List[str]) -> None:
        """
        Initialize the enumerator with a list of CIDR ranges.

        Args:
            cidrs: List of CIDR notation strings (e.g., ['192.168.0.0/24',
                '10.0.0.0/8'])

        Raises:
            ValueError: If any CIDR string is invalid
        """
        logger.debug(f"Initializing NetworkEnumerator with {len(cidrs)} networks: {cidrs}")
        self.networks = []

        for cidr in cidrs:
            network = ipaddress.ip_network(cidr)
            base_int = int(network.network_address)
            partition_size = determine_partition_size(network)
            addr_class = ipaddress.IPv6Address if isinstance(network, ipaddress.IPv6Network) else ipaddress.IPv4Address
            logger.debug(
                f"Network {cidr}: base={base_int}, "
                f"partition_size={partition_size}, "
                f"total_addresses={network.num_addresses}"
            )

            def create_generator(
                net: IPNetwork = network, base: int = base_int, size: int = partition_size, cls: type = addr_class
            ) -> Iterator[int]:
                """Create a generator for a specific network partition."""
                num_partitions = math.ceil(float(net.num_addresses) / size)
                logger.debug(f"Creating generator for {net} with {num_partitions} " f"partitions of size {size}")
                for i in range(int(num_partitions)):
                    start = base + (i * size)
                    end = min(start + size, int(net.broadcast_address) + 1)
                    # Use the correct address class for debug messages
                    start_addr = cls(start)
                    end_addr = cls(end - 1)
                    logger.debug(f"Yielding partition {i+1}/{num_partitions}: " f"addresses {start_addr} to {end_addr}")
                    yield from range(start, end)

            self.networks.append((create_generator(), addr_class))

    def __iter__(self) -> Iterator[IPAddress]:
        """
        Provide synchronous iteration over IP addresses.

        Yields addresses by striping across all networks, converting integer
        representations back to IP addresses.

        Yields:
            IPAddress: IPv4Address or IPv6Address objects
        """
        logger.debug("Starting synchronous iteration")
        active_gens = deque(self.networks)
        addresses_yielded = 0

        while active_gens:
            try:
                gen, addr_class = active_gens[0]
                addr_int = next(gen)
                addr = addr_class(addr_int)
                addresses_yielded += 1
                if addresses_yielded % 10000 == 0:
                    logger.debug(f"Yielded {addresses_yielded} addresses so far")
                yield addr
                active_gens.rotate(-1)
            except StopIteration:
                logger.debug(f"Finished network {active_gens[0][1].__name__}")
                active_gens.popleft()

        logger.debug(f"Enumeration complete. Total addresses yielded: {addresses_yielded}")

    async def __aiter__(self) -> AsyncIterator[IPAddress]:
        """
        Provide asynchronous iteration over IP addresses.

        Similar to __iter__, but yields control back to the event loop periodically
        to allow other tasks to run.

        Yields:
            IPAddress: IPv4Address or IPv6Address objects
        """
        logger.debug("Starting asynchronous iteration")
        active_gens = deque(self.networks)
        addresses_yielded = 0

        while active_gens:
            try:
                gen, addr_class = active_gens[0]
                addr_int = next(gen)
                addr = addr_class(addr_int)
                addresses_yielded += 1
                if addresses_yielded % 10000 == 0:
                    logger.debug(f"Yielded {addresses_yielded} addresses so far")
                yield addr
                active_gens.rotate(-1)
                await asyncio.sleep(0)
            except StopIteration:
                logger.debug(f"Finished network {active_gens[0][1].__name__}")
                active_gens.popleft()

        logger.debug(f"Async enumeration complete. Total addresses yielded: {addresses_yielded}")


def netenum(cidrs: List[str]) -> Iterator[IPAddress]:
    """
    Create a synchronous iterator over IP addresses from multiple CIDR ranges.

    This is the main entry point for synchronous enumeration of IP addresses.
    It stripes across all provided networks, yielding addresses from each in turn.

    Args:
        cidrs: List of CIDR notation strings (e.g., ['192.168.0.0/24',
            '10.0.0.0/8'])

    Returns:
        Iterator yielding IPv4Address or IPv6Address objects

    Examples:
        >>> for addr in netenum(['192.168.0.0/24', '10.0.0.0/8']):
        ...     print(addr)
        192.168.0.0
        10.0.0.0
        192.168.0.1
        10.0.0.1
        # ... and so on

    Raises:
        ValueError: If any CIDR string is invalid
    """
    logger.debug(f"Creating synchronous enumerator for networks: {cidrs}")
    return iter(NetworkEnumerator(cidrs))


async def aionetenum(cidrs: List[str]) -> AsyncIterator[IPAddress]:
    """
    Create an asynchronous iterator over IP addresses from multiple CIDR ranges.

    This is the main entry point for asynchronous enumeration of IP addresses.
    It works the same way as netenum() but can be used with async for.

    Args:
        cidrs: List of CIDR notation strings (e.g., ['192.168.0.0/24',
            '10.0.0.0/8'])

    Returns:
        AsyncIterator yielding IPv4Address or IPv6Address objects

    Examples:
        >>> async for addr in await aionetenum(['192.168.0.0/24']):
        ...     print(addr)
        192.168.0.0
        192.168.0.1
        # ... and so on

    Raises:
        ValueError: If any CIDR string is invalid
    """
    logger.debug(f"Creating asynchronous enumerator for networks: {cidrs}")
    return NetworkEnumerator(cidrs).__aiter__()
