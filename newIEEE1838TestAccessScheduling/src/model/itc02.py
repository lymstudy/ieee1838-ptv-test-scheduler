from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Itc02Test:
    test_id: int
    scan_use: int
    tam_use: int
    patterns: int


@dataclass(frozen=True)
class Itc02Module:
    module_id: int
    level: int
    inputs: int
    outputs: int
    bidirs: int
    scan_chains: tuple[int, ...]
    tests: tuple[Itc02Test, ...]

    @property
    def pattern_count(self) -> int:
        return sum(test.patterns for test in self.tests)

    @property
    def chain_count(self) -> int:
        return len(self.scan_chains)

    @property
    def max_chain_length_bits(self) -> int:
        if self.scan_chains:
            return max(self.scan_chains)
        return max(1, self.inputs + self.outputs + self.bidirs)

    @property
    def total_chain_length_bits(self) -> int:
        if self.scan_chains:
            return sum(self.scan_chains)
        return self.max_chain_length_bits


@dataclass(frozen=True)
class Itc02Soc:
    soc_name: str
    total_modules: int
    modules: tuple[Itc02Module, ...]

    @property
    def leaf_modules(self) -> tuple[Itc02Module, ...]:
        return tuple(module for module in self.modules if module.tests)


def parse_soc_file(path: str | Path) -> Itc02Soc:
    source = Path(path)
    soc_name = ""
    total_modules = 0
    modules: dict[int, dict[str, object]] = {}
    tests: dict[int, list[Itc02Test]] = {}

    for raw_line in source.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("SocName "):
            soc_name = line.split(maxsplit=1)[1]
            continue
        if line.startswith("TotalModules "):
            total_modules = int(line.split()[1])
            continue

        module_match = re.match(
            r"Module\s+(\d+)\s+Level\s+(\d+)\s+Inputs\s+(\d+)\s+Outputs\s+(\d+)\s+Bidirs\s+(\d+)\s+ScanChains\s+(\d+)\s*:\s*(.*)",
            line,
        )
        if module_match:
            module_id = int(module_match.group(1))
            chain_count = int(module_match.group(6))
            chain_lengths = tuple(int(value) for value in module_match.group(7).split())
            if chain_count != len(chain_lengths):
                raise ValueError(f"{source}: module {module_id} declares {chain_count} scan chains but lists {len(chain_lengths)}")
            modules[module_id] = {
                "module_id": module_id,
                "level": int(module_match.group(2)),
                "inputs": int(module_match.group(3)),
                "outputs": int(module_match.group(4)),
                "bidirs": int(module_match.group(5)),
                "scan_chains": chain_lengths,
            }
            continue

        test_match = re.match(
            r"Module\s+(\d+)\s+Test\s+(\d+)\s+ScanUse\s+(\d+)\s+TamUse\s+(\d+)\s+Patterns\s+(\d+)",
            line,
        )
        if test_match:
            module_id = int(test_match.group(1))
            tests.setdefault(module_id, []).append(
                Itc02Test(
                    test_id=int(test_match.group(2)),
                    scan_use=int(test_match.group(3)),
                    tam_use=int(test_match.group(4)),
                    patterns=int(test_match.group(5)),
                )
            )

    if not soc_name:
        raise ValueError(f"{source}: missing SocName")

    parsed_modules = []
    for module_id in sorted(modules):
        data = modules[module_id]
        parsed_modules.append(
            Itc02Module(
                module_id=module_id,
                level=int(data["level"]),
                inputs=int(data["inputs"]),
                outputs=int(data["outputs"]),
                bidirs=int(data["bidirs"]),
                scan_chains=tuple(data["scan_chains"]),
                tests=tuple(tests.get(module_id, [])),
            )
        )
    return Itc02Soc(soc_name=soc_name, total_modules=total_modules, modules=tuple(parsed_modules))
