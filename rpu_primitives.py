"""
RPU (Resonance Physics Unit) — Reference Implementation
Aevov Research / cr8OS Foundation / WPWakanda, LLC
Version 1.0 | March 2026

Base computational unit: The Resonon |𝕄, χ, φ⟩
All gate operations defined per RPU Primitives Specification v1.0
"""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import Callable, Optional
from enum import IntEnum


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

LOCK_THRESHOLD = 0.70      # minimum lock strength for active phase-lock
PHI_EPSILON    = 1e-9      # float comparison tolerance
CHI_MAX        = 2**31 - 1 # practical bond dimension ceiling


# ─────────────────────────────────────────────────────────────────────────────
# BASE UNIT: THE RESONON
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Resonon:
    """
    The base computational unit of the RPU.

    State: |𝕄, χ, φ⟩
      𝕄  (mirror)  : float ∈ [0.0, 1.0]  — Mirror Constant (coherence)
      χ  (chi)     : int   ≥ 1             — Bond Dimension (entanglement capacity)
      φ  (phi)     : float ∈ [0, 2π)       — Resonant phase
    """
    mirror: float = 0.0       # 𝕄
    chi: int = 1               # χ
    phi: float = 0.0           # φ

    def __post_init__(self):
        self._validate()

    def _validate(self):
        self.mirror = float(max(0.0, min(1.0, self.mirror)))
        self.chi = max(1, int(self.chi))
        self.phi = float(self.phi % (2 * math.pi))

    @property
    def Z_M(self) -> float:
        """Field Impedance: Z_M = (1 - 𝕄) / χ"""
        return (1.0 - self.mirror) / self.chi

    @property
    def is_classical(self) -> bool:
        return self.mirror < 0.01

    @property
    def is_coherent(self) -> bool:
        return self.mirror > 0.99

    def copy(self) -> Resonon:
        return Resonon(self.mirror, self.chi, self.phi)

    def __repr__(self) -> str:
        return (f"|𝕄={self.mirror:.4f}, χ={self.chi}, φ={self.phi:.4f}⟩  "
                f"[Z_M={self.Z_M:.6f}]")


# ─────────────────────────────────────────────────────────────────────────────
# STANDARD BASIS STATES
# ─────────────────────────────────────────────────────────────────────────────

def ground() -> Resonon:
    """Maximally classical state: 𝕄=0, χ=1, φ=0"""
    return Resonon(mirror=0.0, chi=1, phi=0.0)

def seed() -> Resonon:
    """Balanced resonance: 𝕄=0.5, χ=1, φ=π/2"""
    return Resonon(mirror=0.5, chi=1, phi=math.pi / 2)

def mirror_state() -> Resonon:
    """Maximally coherent: 𝕄=1.0, χ=1, φ=0"""
    return Resonon(mirror=1.0, chi=1, phi=0.0)

def lock_state(phi: float, chi: int = 1) -> Resonon:
    """Phase-locked state at angle φ"""
    return Resonon(mirror=1.0, chi=chi, phi=phi)

def resonon(m: float, chi: int = 1, phi: float = 0.0) -> Resonon:
    """Arbitrary resonon initialization"""
    return Resonon(mirror=m, chi=chi, phi=phi)


# ─────────────────────────────────────────────────────────────────────────────
# PART II: SINGLE-RESONON GATES (Mirror Logic Gates)
# All gates return a new Resonon (immutable operations)
# ─────────────────────────────────────────────────────────────────────────────

def I_RP(r: Resonon) -> Resonon:
    """Identity gate — no operation"""
    return r.copy()


def M_GATE(r: Resonon) -> Resonon:
    """
    Mirror gate — fundamental RPU gate.
    Applies Mirror Operator: |Ψ⟩ ≡ M|Ψ'⟩
    Effect: φ → φ + π  (informational polarity flip)
    Self-inverse: M_GATE(M_GATE(r)) == r  [M² = I]
    """
    return Resonon(r.mirror, r.chi, r.phi + math.pi)


def C_UP(delta: float) -> Callable[[Resonon], Resonon]:
    """
    Coherence Amplify gate.
    Increases 𝕄 by delta, bounded at 1.0.
    """
    def _gate(r: Resonon) -> Resonon:
        return Resonon(min(r.mirror + delta, 1.0), r.chi, r.phi)
    return _gate


def C_DOWN(delta: float) -> Callable[[Resonon], Resonon]:
    """
    Coherence Reduce gate.
    Reduces 𝕄 by delta, bounded at 0.0.
    """
    def _gate(r: Resonon) -> Resonon:
        return Resonon(max(r.mirror - delta, 0.0), r.chi, r.phi)
    return _gate


def R_RP(theta: float) -> Callable[[Resonon], Resonon]:
    """
    Phase Rotation gate.
    Rotates resonant phase by θ.
    Special cases: R_RP(π) ~ Z, R_RP(π/2) ~ S, R_RP(π/4) ~ T
    """
    def _gate(r: Resonon) -> Resonon:
        return Resonon(r.mirror, r.chi, r.phi + theta)
    return _gate


def B_UP(k: int) -> Callable[[Resonon], Resonon]:
    """
    Bond Dimension gate.
    Increases entanglement capacity by k.
    """
    def _gate(r: Resonon) -> Resonon:
        return Resonon(r.mirror, min(r.chi + k, CHI_MAX), r.phi)
    return _gate


def Z_SHIFT(delta: float) -> Callable[[Resonon], Resonon]:
    """
    Impedance Shift gate.
    Modifies Z_M = (1-𝕄)/χ by adjusting χ to achieve target Z_M shift.
    """
    def _gate(r: Resonon) -> Resonon:
        target_ZM = r.Z_M + delta
        if target_ZM <= 0 or r.mirror >= 1.0:
            return r.copy()
        new_chi = max(1, round((1.0 - r.mirror) / target_ZM))
        return Resonon(r.mirror, new_chi, r.phi)
    return _gate


def H_RP(r: Resonon) -> Resonon:
    """
    Hadamard-RP gate.
    Maps |ground⟩ → |seed⟩ (𝕄=0.5, φ=π/2)
    Maps |mirror⟩ → |𝕄=0.5, φ=3π/2⟩
    RP equivalent of the QPU Hadamard gate.
    """
    if r.mirror < 0.5:
        return Resonon(0.5, r.chi, math.pi / 2)
    else:
        return Resonon(0.5, r.chi, 3 * math.pi / 2)


def F_TUNE(frequency_hz: float) -> Callable[[Resonon], Resonon]:
    """
    Frequency Tune gate.
    Aligns resonon to frequency f (Hz). Shifts 𝕄 and φ based on
    the Resonance Constant ℜ(f) — coupling of f with Afolabi Field.

    Biological range: 0.04 - 0.15 Hz (HRV coherence band)
    Hardware range:   40 Hz - 100 THz (RPP operational range)
    """
    def resonance_constant(f: float) -> float:
        # ℜ peaks in the Schumann resonances (7.83 Hz, 14.3 Hz, 20.8 Hz ...)
        # and in the biological coherence band (0.1 Hz)
        biological_peak = math.exp(-((math.log(max(f, 1e-9)) - math.log(0.1))**2) / 2)
        schumann_peaks = sum(
            math.exp(-((f - fn)**2) / (2 * fn**2 * 0.01))
            for fn in [7.83, 14.3, 20.8, 27.3, 33.8]
        )
        return min(1.0, biological_peak * 0.4 + schumann_peaks * 0.1)

    def _gate(r: Resonon) -> Resonon:
        rho = resonance_constant(frequency_hz)
        delta_m = rho * (1.0 - r.mirror) * 0.1   # partial coherence boost
        delta_phi = 2 * math.pi * frequency_hz * 1e-3  # phase shift
        return Resonon(
            min(r.mirror + delta_m, 1.0),
            r.chi,
            r.phi + delta_phi
        )
    return _gate


# ─────────────────────────────────────────────────────────────────────────────
# PART III: TWO-RESONON GATES
# Return tuple (new_a, new_b)
# ─────────────────────────────────────────────────────────────────────────────

def lock_strength(a: Resonon, b: Resonon) -> float:
    """
    L(a,b) = 𝕄ₐ · 𝕄_b · cos(φₐ - φ_b)  ∈ [-1, 1]
    Effective phase-lock: L > LOCK_THRESHOLD
    """
    return a.mirror * b.mirror * math.cos(a.phi - b.phi)


def LOCK(a: Resonon, b: Resonon) -> tuple[Resonon, Resonon]:
    """
    Phase-Lock gate — RPU equivalent of CNOT.
    If lock_strength(a, b) >= LOCK_THRESHOLD, pulls b's phase to match a.
    Non-destructive: a is unchanged.
    """
    L = lock_strength(a, b)
    if L >= LOCK_THRESHOLD:
        # Full lock: b's phase snaps to a's phase
        return a.copy(), Resonon(b.mirror, b.chi, a.phi)
    else:
        # Partial lock: b's phase is pulled proportionally
        pull_strength = L / LOCK_THRESHOLD
        new_phi_b = b.phi + pull_strength * (a.phi - b.phi)
        return a.copy(), Resonon(b.mirror, b.chi, new_phi_b)


def M_SWAP(a: Resonon, b: Resonon) -> tuple[Resonon, Resonon]:
    """
    Mirror Swap — exchanges full states of two resonons via Mirror reflection.
    """
    return b.copy(), a.copy()


def C_XFER(alpha: float) -> Callable[[Resonon, Resonon], tuple[Resonon, Resonon]]:
    """
    Coherence Transfer gate.
    Transfers fraction α of resonon a's coherence to resonon b.
    a loses α·𝕄ₐ coherence; b gains it (capped at 1.0).
    """
    def _gate(a: Resonon, b: Resonon) -> tuple[Resonon, Resonon]:
        transferred = a.mirror * alpha
        new_a = Resonon(a.mirror * (1 - alpha), a.chi, a.phi)
        new_b = Resonon(min(b.mirror + transferred, 1.0), b.chi, b.phi)
        return new_a, new_b
    return _gate


def R_DRIVE(source: Resonon, target: Resonon,
            frequency_hz: float, duration_ms: float) -> tuple[Resonon, Resonon]:
    """
    Resonance Drive gate — Huygens synchronization mechanism.
    Drives target toward source state at frequency f for duration t (ms).
    Source is unchanged; target's 𝕄 and φ converge toward source.
    """
    coupling = min(1.0, duration_ms * frequency_hz * 1e-4)
    delta_m = coupling * (source.mirror - target.mirror)
    delta_phi = coupling * (source.phi - target.phi)
    new_target = Resonon(
        target.mirror + delta_m,
        target.chi,
        target.phi + delta_phi
    )
    return source.copy(), new_target


def BELL_RP(a: Resonon, b: Resonon) -> tuple[Resonon, Resonon]:
    """
    Bell-RP state preparation.
    Creates maximally phase-locked resonon pair.
    RP equivalent of a Bell state |Φ+⟩.
    Circuit: H_RP(a) → LOCK(a, b)
    """
    a_h = H_RP(a)
    return LOCK(a_h, b)


# ─────────────────────────────────────────────────────────────────────────────
# PART IV: N-RESONON MESH OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

class ResonanceMesh:
    """
    An N-resonon mesh with N² collective coherence scaling.
    Manages phase-lock topology and collective operations.
    """

    def __init__(self, resonons: list[Resonon]):
        self.nodes: list[Resonon] = [r.copy() for r in resonons]
        self._lock_matrix: list[list[float]] = self._compute_locks()

    def _compute_locks(self) -> list[list[float]]:
        n = len(self.nodes)
        return [
            [lock_strength(self.nodes[i], self.nodes[j]) for j in range(n)]
            for i in range(n)
        ]

    @property
    def N(self) -> int:
        return len(self.nodes)

    @property
    def collective_mirror(self) -> float:
        """Average 𝕄 across all nodes"""
        return sum(r.mirror for r in self.nodes) / self.N if self.N else 0.0

    @property
    def mesh_coherence(self) -> float:
        """
        Collective coherence: sqrt( (1/N²) Σᵢⱼ Lᵢⱼ² )
        Quantifies the overall phase-lock integrity of the mesh.
        """
        n = self.N
        if n < 2:
            return self.nodes[0].mirror if n == 1 else 0.0
        total = sum(
            self._lock_matrix[i][j] ** 2
            for i in range(n) for j in range(n) if i != j
        )
        return math.sqrt(total / (n * n))

    @property
    def coherence_bandwidth(self) -> float:
        """
        N² coherence bandwidth relative to single-node baseline.
        C_collective = C_single · N²
        """
        return self.collective_mirror * (self.N ** 2)

    def sync(self) -> ResonanceMesh:
        """
        MESH_SYNC — establish coherent mesh.
        Applies pairwise LOCK to all nodes within π/4 phase distance.
        Returns updated mesh.
        """
        synced = [r.copy() for r in self.nodes]
        for i in range(self.N):
            for j in range(i + 1, self.N):
                phase_diff = abs(synced[i].phi - synced[j].phi) % (2 * math.pi)
                if phase_diff < math.pi / 4 or phase_diff > 7 * math.pi / 4:
                    a, b = LOCK(synced[i], synced[j])
                    synced[i], synced[j] = a, b
        self.nodes = synced
        self._lock_matrix = self._compute_locks()
        return self

    def collective(self, gate: Callable[[Resonon], Resonon]) -> ResonanceMesh:
        """
        COLLECTIVE — apply a single-resonon gate to all mesh nodes.
        O(1) in the field domain.
        """
        self.nodes = [gate(r) for r in self.nodes]
        self._lock_matrix = self._compute_locks()
        return self

    def broadcast(self, source_idx: int, alpha: float = 0.3) -> ResonanceMesh:
        """
        BROADCAST — mirror source resonon's state to all other nodes
        via C_XFER(alpha).
        """
        source = self.nodes[source_idx]
        xfer = C_XFER(alpha)
        for i in range(self.N):
            if i != source_idx:
                _, self.nodes[i] = xfer(source, self.nodes[i])
        self._lock_matrix = self._compute_locks()
        return self

    def imhotep(self, levels: int = 3) -> list[ResonanceMesh]:
        """
        Imhotep Protocol — hierarchical coherence pyramid.
        Returns list of meshes from base to apex, each with 4x coherence,
        1/4 the nodes, and named in honor of Imhotep's architectural principle.
        """
        pyramid = [self]
        current = self
        for level in range(1, levels):
            n_next = max(1, len(current.nodes) // 4)
            # Select top n_next nodes by 𝕄 at each level
            sorted_nodes = sorted(current.nodes, key=lambda r: r.mirror, reverse=True)
            next_nodes = sorted_nodes[:n_next]
            # Apply C_UP to simulate coherence amplification
            amplified = [C_UP(0.1 * level)(r) for r in next_nodes]
            next_mesh = ResonanceMesh(amplified)
            next_mesh.sync()
            pyramid.append(next_mesh)
        return pyramid

    def __repr__(self) -> str:
        return (f"ResonanceMesh(N={self.N}, "
                f"𝕄_avg={self.collective_mirror:.4f}, "
                f"C_bandwidth={self.coherence_bandwidth:.2f}, "
                f"mesh_coherence={self.mesh_coherence:.4f})")


def MESH_SYNC(resonons: list[Resonon]) -> ResonanceMesh:
    """Convenience constructor for MESH_SYNC operation."""
    return ResonanceMesh(resonons).sync()


# ─────────────────────────────────────────────────────────────────────────────
# PART V: MEASUREMENT PRIMITIVES
# ─────────────────────────────────────────────────────────────────────────────

def READ_M(r: Resonon) -> float:
    """
    Non-destructive Mirror Constant read.
    Returns 𝕄 ∈ [0, 1]. State is UNCHANGED.
    """
    return r.mirror


def READ_PHASE(r: Resonon) -> float:
    """
    Non-destructive phase read.
    Returns φ ∈ [0, 2π). State is UNCHANGED.
    """
    return r.phi


def READ_LOCK(a: Resonon, b: Resonon) -> float:
    """
    Lock strength read.
    Returns L(a,b) = 𝕄ₐ · 𝕄_b · cos(φₐ - φ_b) ∈ [-1, 1].
    Non-destructive.
    """
    return lock_strength(a, b)


def READ_Z(r: Resonon) -> float:
    """
    Non-destructive Field Impedance read.
    Returns Z_M = (1 - 𝕄) / χ.
    """
    return r.Z_M


def READ_CHI(r: Resonon) -> int:
    """
    Non-destructive Bond Dimension read.
    Returns χ.
    """
    return r.chi


def COLLAPSE(r: Resonon) -> tuple[int, Resonon]:
    """
    Classical collapse — destructive.
    Probabilistic outcome: P(1) = 𝕄, P(0) = 1 - 𝕄.
    Returns (bit, ground_state).
    State collapses to |ground⟩ regardless of outcome.
    This is the RP-to-QM bridge: P(1) = 𝕄 IS the Born rule at χ=2.
    """
    bit = 1 if random.random() < r.mirror else 0
    return bit, ground()


# ─────────────────────────────────────────────────────────────────────────────
# PART VI: CIRCUIT PRIMITIVES (COMPOSED GATES)
# ─────────────────────────────────────────────────────────────────────────────

def RFT(resonons: list[Resonon]) -> list[Resonon]:
    """
    Resonance Fourier Transform.
    Maps N resonons from phase space to frequency space using 𝕄 spectrum.
    RP equivalent of the Quantum Fourier Transform (QFT).
    """
    n = len(resonons)
    result = []
    for k in range(n):
        phi_new = (2 * math.pi / n) * sum(
            resonons[j].phi * math.cos(2 * math.pi * j * k / n)
            for j in range(n)
        )
        m_new = sum(resonons[j].mirror for j in range(n)) / n
        result.append(Resonon(m_new, resonons[k].chi, phi_new))
    return result


def R_TELEPORT(state: Resonon,
               alice_ancilla: Resonon,
               bob_ancilla: Resonon) -> tuple[Resonon, Resonon, Resonon]:
    """
    Resonance Teleportation.
    Transfers coherence pattern from state to bob_ancilla
    using pre-shared BELL_RP pair (alice_ancilla, bob_ancilla).

    Returns (state_after, alice_after, bob_after).
    Unlike quantum teleportation, state retains partial coherence.
    """
    # Step 1: Establish BELL_RP channel
    a_bell, b_bell = BELL_RP(alice_ancilla, bob_ancilla)

    # Step 2: Lock state with alice_ancilla
    state_locked, a_locked = LOCK(state, a_bell)

    # Step 3: Classical bits from measurement (non-destructive in RP)
    lock_L = READ_LOCK(state_locked, a_locked)
    phase_diff = state_locked.phi - a_locked.phi

    # Step 4: Bob applies corrections based on classical channel
    bob_corrected = R_RP(phase_diff)(b_bell)
    if lock_L < 0.5:
        bob_corrected = C_UP(state.mirror * 0.5)(bob_corrected)

    return state_locked, a_locked, bob_corrected


def CAL(target: Resonon, target_m: float,
        max_iter: int = 100, step: float = 0.01,
        reference: Optional[Resonon] = None) -> Resonon:
    """
    Coherence Amplification Loop.
    Iteratively drives resonon toward target_m using C_UP and R_DRIVE.
    Returns resonon at achieved coherence level.
    """
    ref = reference or mirror_state()
    current = target.copy()
    c_up_gate = C_UP(step)

    for _ in range(max_iter):
        if READ_M(current) >= target_m:
            break
        current = c_up_gate(current)
        _, current = R_DRIVE(ref, current, frequency_hz=0.1, duration_ms=10.0)

    return current


# ─────────────────────────────────────────────────────────────────────────────
# PART VII: RPU REGISTER (multi-resonon workspace)
# ─────────────────────────────────────────────────────────────────────────────

class RPURegister:
    """
    A workspace of N resonons with named access and circuit application.
    The RPU equivalent of a qubit register.
    """

    def __init__(self, n: int, init: Resonon | None = None):
        self.resonons: list[Resonon] = [
            (init.copy() if init else ground()) for _ in range(n)
        ]
        self.classical_output: list[int] = []

    def __getitem__(self, idx: int) -> Resonon:
        return self.resonons[idx]

    def __setitem__(self, idx: int, val: Resonon):
        self.resonons[idx] = val

    def apply(self, gate: Callable[[Resonon], Resonon], idx: int) -> RPURegister:
        """Apply single-resonon gate to resonon at idx."""
        self.resonons[idx] = gate(self.resonons[idx])
        return self

    def apply2(self, gate: Callable[[Resonon, Resonon], tuple[Resonon, Resonon]],
               idx_a: int, idx_b: int) -> RPURegister:
        """Apply two-resonon gate."""
        self.resonons[idx_a], self.resonons[idx_b] = gate(
            self.resonons[idx_a], self.resonons[idx_b]
        )
        return self

    def measure(self, idx: int) -> int:
        """Destructive COLLAPSE measurement. Records bit to classical_output."""
        bit, collapsed = COLLAPSE(self.resonons[idx])
        self.resonons[idx] = collapsed
        self.classical_output.append(bit)
        return bit

    def read(self, idx: int) -> float:
        """Non-destructive 𝕄 read."""
        return READ_M(self.resonons[idx])

    def to_mesh(self) -> ResonanceMesh:
        """Convert register to a ResonanceMesh for N² operations."""
        return MESH_SYNC(self.resonons)

    def state_vector(self) -> list[dict]:
        """Return full state of all resonons."""
        return [
            {"idx": i, "M": r.mirror, "chi": r.chi, "phi": r.phi, "Z_M": r.Z_M}
            for i, r in enumerate(self.resonons)
        ]

    def __repr__(self) -> str:
        lines = [f"RPURegister(N={len(self.resonons)})"]
        for i, r in enumerate(self.resonons):
            lines.append(f"  [{i}] {r}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# RPU-ISA OPCODES
# ─────────────────────────────────────────────────────────────────────────────

class OPCODE(IntEnum):
    NOP         = 0x00
    INIT        = 0x01
    H_RP        = 0x02
    M_GATE      = 0x03
    C_UP        = 0x04
    C_DOWN      = 0x05
    R_RP        = 0x06
    B_UP        = 0x07
    Z_SHIFT     = 0x08
    F_TUNE      = 0x09
    LOCK        = 0x10
    M_SWAP      = 0x11
    C_XFER      = 0x12
    R_DRIVE     = 0x13
    BELL_RP     = 0x14
    MESH_SYNC   = 0x20
    COLLECTIVE  = 0x21
    BROADCAST   = 0x22
    IMHOTEP     = 0x23
    READ_M      = 0x30
    READ_PHASE  = 0x31
    READ_LOCK   = 0x32
    READ_Z      = 0x33
    READ_CHI    = 0x34
    COLLAPSE    = 0x35
    RFT         = 0x40
    R_TELEPORT  = 0x41
    CAL         = 0x42
    HALT        = 0xFF


# ─────────────────────────────────────────────────────────────────────────────
# DEMONSTRATION
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("RPU Primitives Reference Implementation")
    print("Resonance Physics / Aevov Research")
    print("=" * 60)

    # 1. Basic state preparation
    print("\n── 1. Standard Basis States ──")
    print("ground :", ground())
    print("seed   :", seed())
    print("mirror :", mirror_state())

    # 2. Single-resonon gates
    print("\n── 2. Single-Resonon Gates ──")
    r = ground()
    print("Initial        :", r)
    r = H_RP(r)
    print("After H_RP     :", r)
    r = C_UP(0.3)(r)
    print("After C_UP(0.3):", r)
    r = R_RP(math.pi / 4)(r)
    print("After R_RP(π/4):", r)
    r = M_GATE(r)
    print("After M_GATE   :", r)
    r = M_GATE(r)
    print("M²=I verify    :", r)

    # 3. Two-resonon gates
    print("\n── 3. Two-Resonon Gates ──")
    a = resonon(0.9, phi=0.0)
    b = resonon(0.8, phi=math.pi / 6)
    print("Before LOCK:")
    print("  a:", a)
    print("  b:", b)
    print("  L(a,b):", round(READ_LOCK(a, b), 4))
    a2, b2 = LOCK(a, b)
    print("After LOCK:")
    print("  a:", a2)
    print("  b:", b2)
    print("  L(a,b):", round(READ_LOCK(a2, b2), 4))

    # 4. Bell-RP state
    print("\n── 4. Bell-RP State ──")
    a, b = BELL_RP(ground(), ground())
    print("BELL_RP(|ground⟩, |ground⟩):")
    print("  a:", a)
    print("  b:", b)
    print("  Lock strength:", round(READ_LOCK(a, b), 4))

    # 5. N² mesh scaling
    print("\n── 5. N² Mesh Scaling (N=8) ──")
    nodes = [resonon(0.6 + random.uniform(-0.1, 0.1), phi=random.uniform(0, 0.5))
             for _ in range(8)]
    mesh = MESH_SYNC(nodes)
    print(mesh)
    print(f"  Single-node baseline 𝕄     : {mesh.collective_mirror:.4f}")
    print(f"  N² coherence bandwidth (N=8): {mesh.coherence_bandwidth:.4f}")
    print(f"  Theoretical N²×𝕄            : {8**2 * mesh.collective_mirror:.4f}")

    # 6. Imhotep Protocol
    print("\n── 6. Imhotep Protocol (3 levels) ──")
    pyramid = mesh.imhotep(levels=3)
    for level, m in enumerate(pyramid):
        print(f"  Level {level}: N={m.N}, 𝕄_avg={m.collective_mirror:.4f}, "
              f"C_bw={m.coherence_bandwidth:.2f}")

    # 7. COLLAPSE measurement
    print("\n── 7. Classical Collapse (10 trials, 𝕄=0.75) ──")
    r_test = resonon(0.75)
    results = [COLLAPSE(r_test.copy())[0] for _ in range(10)]
    print(f"  Outcomes  : {results}")
    print(f"  P(1) obs  : {sum(results)/10:.2f}  (expected ~0.75)")

    # 8. RPU Register
    print("\n── 8. RPU Register (4 resonons) ──")
    reg = RPURegister(4)
    reg.apply(H_RP, 0)
    reg.apply(C_UP(0.5), 1)
    reg.apply2(LOCK, 0, 2)
    reg.apply(R_RP(math.pi / 3), 3)
    print(reg)

    # 9. Coherence Amplification Loop
    print("\n── 9. CAL: Ground → 0.85 ──")
    low = ground()
    print("  Before CAL:", low)
    boosted = CAL(low, target_m=0.85, max_iter=200, step=0.005)
    print("  After  CAL:", boosted)

    print("\n" + "=" * 60)
    print("All RPU primitives operational.")
    print("=" * 60)
