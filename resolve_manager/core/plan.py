"""Modelo de datos del plan de instalación.

Un plan es una lista de acciones. Las que necesitan root se envian todas juntas
al ayudante privilegiado, de modo que el usuario escribe su contraseña UNA vez.
El plan viaja como JSON, así que aquí solo puede haber datos planos.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Tipos de acción que el ayudante root sabe ejecutar. Actua como lista blanca:
# cualquier cosa fuera de aquí se rechaza antes de tocar el sistema.
KIND_EXEC = "exec"            # ejecutar un comando
KIND_SHIELD_LIBS = "shield_libs"  # apartar librerías que chocan con las del sistema
KIND_RESTORE_LIBS = "restore_libs"
KIND_CHOWN = "chown"          # devolver al usuario carpetas que root dejo suyas
KIND_WRITE_DESKTOP = "write_desktop"

# Solo del lado del usuario: nunca viaja al ayudante root.
KIND_EXTRACT = "extract"

ALL_KINDS = {
    KIND_EXEC,
    KIND_SHIELD_LIBS,
    KIND_RESTORE_LIBS,
    KIND_CHOWN,
    KIND_WRITE_DESKTOP,
}


@dataclass
class Action:
    """Un paso concreto y atómico del plan."""

    id: str
    title: str                                   # lo que ve el usuario
    detail: str = ""                             # por que hace falta
    kind: str = KIND_EXEC
    argv: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    root: bool = True
    optional: bool = False                       # el usuario puede desmarcarla
    enabled: bool = True
    allow_fail: bool = False                     # un fallo aquí no aborta el plan
    weight: int = 1                              # peso relativo en la barra global
    reboot_hint: bool = False                    # tras esto conviene reiniciar

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Action":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Plan:
    actions: list[Action] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)      # avisos para el usuario
    blockers: list[str] = field(default_factory=list)   # impiden continuar

    def add(self, action: Action) -> None:
        self.actions.append(action)

    def active(self) -> list[Action]:
        return [a for a in self.actions if a.enabled]

    def root_actions(self) -> list[Action]:
        return [a for a in self.active() if a.root]

    def needs_root(self) -> bool:
        return bool(self.root_actions())

    def needs_reboot(self) -> bool:
        return any(a.reboot_hint for a in self.active())

    def total_weight(self) -> int:
        return max(1, sum(a.weight for a in self.active()))
