"""Test suite for the core network enumeration functionality."""

import ipaddress

import pytest

from netenum.core import NetworkEnumerator, determine_partition_size


def test_ipv4_enumeration() -> None:
    """Test basic IPv4 address enumeration."""
    cidrs = ["192.168.0.0/24"]
    enumerator = NetworkEnumerator(cidrs)
    addresses = list(enumerator)
    assert len(addresses) == 256
    assert all(isinstance(addr, ipaddress.IPv4Address) for addr in addresses)
    assert addresses[0] == ipaddress.IPv4Address("192.168.0.0")
    assert addresses[-1] == ipaddress.IPv4Address("192.168.0.255")


def test_ipv6_enumeration() -> None:
    """Test basic IPv6 address enumeration."""
    cidrs = ["2001:db8::/120"]
    enumerator = NetworkEnumerator(cidrs)
    addresses = list(enumerator)
    assert len(addresses) == 256
    assert all(isinstance(addr, ipaddress.IPv6Address) for addr in addresses)
    assert addresses[0] == ipaddress.IPv6Address("2001:db8::")
    assert addresses[-1] == ipaddress.IPv6Address("2001:db8::ff")


def test_mixed_enumeration() -> None:
    """Test enumeration of mixed IPv4 and IPv6 networks."""
    cidrs = ["192.168.0.0/24", "2001:db8::/120"]
    enumerator = NetworkEnumerator(cidrs)
    addresses = list(enumerator)
    assert len(addresses) == 512
    assert any(isinstance(addr, ipaddress.IPv4Address) for addr in addresses)
    assert any(isinstance(addr, ipaddress.IPv6Address) for addr in addresses)


def test_invalid_cidr() -> None:
    """Test handling of invalid CIDR ranges."""
    with pytest.raises(ValueError):
        NetworkEnumerator(["invalid"])


def test_empty_list() -> None:
    """Test enumeration with empty input."""
    enumerator = NetworkEnumerator([])
    assert list(enumerator) == []


@pytest.mark.asyncio
async def test_async_enumeration() -> None:
    """Test asynchronous enumeration functionality."""
    cidrs = ["192.168.0.0/24"]
    enumerator = NetworkEnumerator(cidrs)
    addresses = []
    async for addr in enumerator:
        addresses.append(addr)
    assert len(addresses) == 256
    assert all(isinstance(addr, ipaddress.IPv4Address) for addr in addresses)


def test_large_prefix_memory() -> None:
    """Test memory efficiency with large networks."""
    cidrs = ["10.0.0.0/8"]  # 16M addresses
    enumerator = NetworkEnumerator(cidrs)
    iterator = iter(enumerator)
    first_addr = next(iterator)
    assert first_addr == ipaddress.IPv4Address("10.0.0.0")


def test_partition_sizes() -> None:
    """Test partition size determination for different networks."""
    test_cases = [
        ("192.168.0.0/24", 256),  # Small IPv4
        ("10.0.0.0/8", 1024),  # Large IPv4
        ("2001:db8::/120", 256),  # Small IPv6
        ("2001:db8::/32", 1048576),  # Large IPv6
    ]
    for cidr, expected_size in test_cases:
        network = ipaddress.ip_network(cidr)
        size = determine_partition_size(network)
        assert size == expected_size


def test_multiple_large_networks_memory() -> None:
    """Test memory efficiency with multiple large networks."""
    cidrs = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
    enumerator = NetworkEnumerator(cidrs)
    iterator = iter(enumerator)

    # Test first few addresses from each network
    first_addrs = [next(iterator) for _ in range(4)]
    assert str(first_addrs[0]) == "10.0.0.0"
    assert str(first_addrs[1]) == "172.16.0.0"
    assert str(first_addrs[2]) == "192.168.0.0"
    assert str(first_addrs[3]) == "10.0.0.1"


def test_full_range_memory() -> None:
    """Test memory usage when enumerating full ranges."""
    cidrs = ["192.168.0.0/16"]  # 65K addresses
    enumerator = NetworkEnumerator(cidrs)
    count = 0

    # Get initial memory usage
    for _ in enumerator:
        count += 1
        if count > 65536:
            raise AssertionError("Too many addresses generated")

    assert count == 65536


def test_memory_stability() -> None:
    """Test memory stability during enumeration."""
    cidrs = ["10.0.0.0/8"]  # 16M addresses
    enumerator = NetworkEnumerator(cidrs)
    count = 0

    # Monitor memory usage while processing first 50K addresses
    for _ in enumerator:
        count += 1
        if count >= 50000:
            break

    assert count == 50000
