import getpass
import hashlib
import os
import random
import time
from typing import List


# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

SYSTEM_SEED_A = 84729104


# ─────────────────────────────────────────────
#  PASSWORD → SEED CONVERSION
# ─────────────────────────────────────────────

def password_to_seed(password: str) -> int:
    """
    Deterministically converts a password into a large integer seed.
    Uses the first 8 bytes of the SHA-256 hash of the password.
    Same password always produces the same seed — and therefore
    the same sequence. Different password, different sequence entirely.
    """
    hash_bytes = hashlib.sha256(password.encode()).digest()
    return int.from_bytes(hash_bytes[:8], byteorder='big')


# ─────────────────────────────────────────────
#  ACCESS LAYER
# ─────────────────────────────────────────────

def get_password(prompt: str) -> str:
    """Prompt for a password without echoing it to the terminal."""
    return getpass.getpass(prompt)


def setup_and_get_seed() -> int:
    """
    First-run wizard and returning-user login combined.

    First run  : prompts the user to create a password, confirms it,
                 then derives Seed B from it and returns it.
    Every run  : same prompt, same derivation, same seed.

    No hash file is stored. The password itself is the key —
    whoever knows it can reproduce the exact same sequence.
    """
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║      2-SEED STRICT SEQUENCE GENERATOR            ║")
    print("  ║      Expanding Block  ·  Base-7  ·  Aperiodic    ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()
    print("  Your password is your seed.")
    print("  The same password always produces the same sequence.")
    print("  There is no stored file — whoever knows the password")
    print("  can reproduce and verify your sequence exactly.\n")

    while True:
        pw = get_password("  Choose your password: ")
        if not pw:
            print("  [!] Password cannot be empty. Try again.\n")
            continue
        confirm = get_password("  Confirm your password: ")
        if pw == confirm:
            seed_b = password_to_seed(pw)
            print(f"\n  [✓] Password accepted.")
            print(f"  [✓] Seed B derived: {seed_b}\n")
            return seed_b
        else:
            print("  [!] Passwords did not match. Try again.\n")


def returning_user_get_seed() -> int:
    """
    For returning users who already know their password.
    Derives Seed B directly — no confirmation needed.
    """
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║      2-SEED STRICT SEQUENCE GENERATOR            ║")
    print("  ║      Expanding Block  ·  Base-7  ·  Aperiodic    ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()
    print("  Your password generates your personal sequence.")
    print("  Same password = same sequence, every time.\n")

    pw = get_password("  Enter your password: ")
    seed_b = password_to_seed(pw)
    print(f"\n  [✓] Seed B derived: {seed_b}\n")
    return seed_b


def get_seed_b() -> int:
    """
    Entry point for the access layer.
    Asks whether this is a first run or returning session,
    then routes accordingly.
    """
    print()
    choice = input("  First time using this program? (y / n): ").strip().lower()
    if choice == 'y':
        return setup_and_get_seed()
    else:
        return returning_user_get_seed()


# ─────────────────────────────────────────────
#  GENERATOR
# ─────────────────────────────────────────────

class TwoSeedRejectionGenerator:
    """
    2-Seed Strict Expanding Block Sequence Generator.

    Produces a continuous stream of Base-7 digits (0–6) divided into
    expanding blocks of size 2k (k = 2, 3, 4, …).

    First half  [0, k)  — Historical Baseline, generated freely.
    Second half [k, 2k) — every digit must differ from its Historical
                          Twin exactly k positions behind it in the archive.
                          Candidates that match are discarded and re-rolled.

    Seed A : hardcoded system constant — one Mersenne Twister engine.
    Seed B : derived from the user's password — second Mersenne Twister engine.

    Both engines are independent Python random.Random instances (Mersenne
    Twister MT19937). Their outputs are mixed at every generation step:

        digit = (gen_a.sample + gen_b.sample) mod 7

    The same password always produces the same Seed B and therefore
    the same sequence. The sequence is the user's personal artifact.
    """

    def __init__(self, seed_a: int, seed_b: int) -> None:
        self.digits_archive:         List[int] = []
        self.current_k:              int       = 2
        self.block_digits_generated: int       = 0
        self.runway_generated:       bool      = False

        # Two independent Mersenne Twister engines (Python random.Random = MT19937)
        self.gen_a = random.Random(seed_a)
        self.gen_b = random.Random(seed_b)

    def _roll(self) -> int:
        """Draw one raw Base-7 candidate by mixing both MT engines."""
        return (self.gen_a.randint(0, 100) + self.gen_b.randint(0, 100)) % 7

    def generate_runway(self) -> None:
        """Generate the 20-digit unrestricted Historical Baseline."""
        for _ in range(20):
            self.digits_archive.append(self._roll())
        self.runway_generated = True

    def generate_next_digit(self) -> int:
        """
        Return the next digit in the sequence.

        Advances the block counter and enforces the strict second-half
        constraint when the current position falls in [k, 2k).
        """
        if not self.runway_generated:
            raise RuntimeError("Call generate_runway() before generating digits.")

        if self.block_digits_generated >= (2 * self.current_k):
            self.current_k              += 1
            self.block_digits_generated  = 0

        if self.block_digits_generated >= self.current_k:
            # ── STRICT CONSTRAINT ──────────────────────────────────────
            # Look back exactly k steps to find the Historical Twin.
            # The twin always falls in the first half of the same block —
            # this guarantees the independence of each constraint event.
            twin = self.digits_archive[len(self.digits_archive) - self.current_k]
            while True:
                digit = self._roll()
                if digit != twin:
                    break
        else:
            digit = self._roll()

        self.digits_archive.append(digit)
        self.block_digits_generated += 1
        return digit

    @property
    def total_generated(self) -> int:
        return len(self.digits_archive)


# ─────────────────────────────────────────────
#  VERIFICATION
# ─────────────────────────────────────────────

def verify_sequence_integrity(
    sequence: List[int],
    initial_runway_length: int = 20
) -> bool:
    """
    Independently verify the structural guarantee of the sequence.

    Walks every block and confirms that no second-half digit matches
    its Historical Twin. Requires no seeds — the rule is self-evident
    from the archive and block structure alone.
    """
    print("\n  ── Independent Audit ──────────────────────────────")
    print("  Scanning archive for constraint violations...\n")

    global_idx        = initial_runway_length
    k                 = 2
    blocks_checked    = 0
    positions_checked = 0

    while global_idx < len(sequence):
        block_length = min(2 * k, len(sequence) - global_idx)

        for local_pos in range(block_length):
            if local_pos >= k:
                current_global = global_idx + local_pos
                twin_index     = current_global - k

                if sequence[current_global] == sequence[twin_index]:
                    print(f"  [FAIL] Violation at index {current_global}.")
                    print(f"         Digit {sequence[current_global]} matches "
                          f"twin at index {twin_index}  (k={k})")
                    return False

                positions_checked += 1

        blocks_checked += 1
        global_idx     += (2 * k)
        k              += 1

    print(f"  Blocks checked    : {blocks_checked}")
    print(f"  Positions checked : {positions_checked}")
    print("\n  [✓] Audit passed. Every constraint was satisfied.")
    print("\n  Note: this verification required no seeds or passwords.")
    print("  Anyone who knows the rule can confirm this sequence")
    print("  is authentic — no secret information needed to verify,")
    print("  only to reproduce.")
    print("  ───────────────────────────────────────────────────\n")
    return True


# ─────────────────────────────────────────────
#  OUTPUT HELPERS
# ─────────────────────────────────────────────

def print_distribution(digits: List[int]) -> None:
    """Print a simple frequency table for the generated digits."""
    total = len(digits)
    print("\n  ── Digit Distribution ─────────────────────────────")
    for d in range(7):
        count = digits.count(d)
        bar   = "█" * (count * 30 // total)
        print(f"  {d} │ {bar:<30} {count:>5}  ({100 * count / total:.1f}%)")
    print("  ───────────────────────────────────────────────────\n")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main() -> None:

    # ── Access layer — password becomes Seed B ──
    seed_b = get_seed_b()

    # ── Target count ────────────────────────────
    while True:
        try:
            target = int(input("  How many Base-7 digits would you like to generate? ").strip())
            if target > 0:
                break
            print("  [!] Please enter a positive number.\n")
        except ValueError:
            print("  [!] Please enter a whole number.\n")

    # ── Initialise ──────────────────────────────
    print(f"\n  System Seed A : {SYSTEM_SEED_A}  (Mersenne Twister A)")
    print(f"  User   Seed B : {seed_b}  (Mersenne Twister B — derived from your password)\n")

    generator = TwoSeedRejectionGenerator(SYSTEM_SEED_A, seed_b)

    print("  Building 20-digit Historical Baseline runway...")
    generator.generate_runway()

    print(f"  Generating {target:,} digits...\n")
    print("  ── Sequence ───────────────────────────────────────")

    generated: List[int] = []
    for i in range(target):
        digit = generator.generate_next_digit()
        generated.append(digit)
        print(digit, end=" ", flush=True)
        if (i + 1) % 40 == 0:
            print(f"\n  {i+1:>6} │ ", end="")

    print("\n  ───────────────────────────────────────────────────")
    print(f"\n  Done. {target:,} digits generated.")
    print(f"  Archive total (runway + generated): {generator.total_generated:,} digits.")

    print_distribution(generated)
    verify_sequence_integrity(generator.digits_archive)

    print("\n  Session complete. Goodbye.\n")


if __name__ == "__main__":
    main()
