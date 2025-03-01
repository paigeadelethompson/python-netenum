# Netenum

Efficient IP address enumerator that interpolates across IPv4 and IPv6 CIDR ranges without expanding full ranges in memory.

## Features

- Supports both IPv4 and IPv6 CIDR ranges
- Memory efficient - doesn't expand full ranges
- Intelligent partitioning based on network size
- Stripes across multiple networks for balanced enumeration
- Supports both synchronous and asynchronous iteration
- Command-line interface with stdin input

## Installation

```bash
pip install netenum
```

## Usage

### Command Line

Enumerate addresses in sequence:
```bash
echo "192.168.1.0/24
10.0.0.0/8" | python -m netenum
```

Enumerate addresses in random order:
```bash
echo "192.168.1.0/24
10.0.0.0/8" | python -m netenum -r
```

You can also use a file:
```bash
cat cidrs.txt | python -m netenum
```

### Python API

#### Synchronous Usage

```python
from netenum import netenum

cidrs = [
    "192.168.0.0/16",          # IPv4
    "2001:db8::/32",           # IPv6
    "224.0.0.0/4",             # IPv4
]

for addr in netenum(cidrs):
    print(addr)
```

#### Asynchronous Usage

```python
import asyncio
from netenum import aionetenum

cidrs = [
    "192.168.0.0/16",          # IPv4
    "2001:db8::/32",           # IPv6
    "224.0.0.0/4",             # IPv4
]

async def main():
    async for addr in await aionetenum(cidrs):
        print(addr)

asyncio.run(main())
```

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:
```bash
pytest
```

Format code:
```bash
black .
isort .
```

Type check:
```bash
mypy .
``` 