"""
Sample selection solver

Main ideas used here:
1. Use bitmask to represent groups
2. Precompute which targets each candidate can cover
3. Use greedy selection, then do a simple pruning step
4. Run greedy several times with different candidate orders
"""

import random
import time
from itertools import combinations
from math import comb
from typing import Any, Dict, List, Sequence, Tuple


# -----------------------------
# 1) Basic checking
# -----------------------------
def check_parameters(m: int, n: int, k: int, j: int, s: int) -> Tuple[bool, str]:
    if not (45 <= m <= 54):
        return False, "m must be between 45 and 54"
    if not (7 <= n <= 25):
        return False, "n must be between 7 and 25"
    if not (4 <= k <= 7):
        return False, "k must be between 4 and 7"
    if not (3 <= s <= 7):
        return False, "s must be between 3 and 7"
    if not (s <= j <= k):
        return False, "j must satisfy s <= j <= k"
    if n < k:
        return False, "n must be >= k"
    return True, "Parameters are valid"


def check_samples(samples: Sequence[int], m: int, n: int) -> Tuple[bool, str]:
    if not isinstance(samples, (list, tuple)):
        return False, "samples must be a list or tuple"
    if len(samples) != n:
        return False, f"the number of samples must equal n ({n})"
    if len(set(samples)) != n:
        return False, "duplicate values are not allowed"
    if any(not isinstance(x, int) for x in samples):
        return False, "all elements must be integers"
    if any(x < 1 or x > m for x in samples):
        return False, f"elements must be within 1..{m}"
    return True, "Samples are valid"


# -----------------------------
# 2) Bitmask helpers
# -----------------------------
def to_mask(group: Sequence[int]) -> int:
    """Convert a group like (1, 3, 5) to a bitmask."""
    mask = 0
    for x in group:
        mask |= 1 << (x - 1)
    return mask


def is_covered_mask(k_mask: int, j_mask: int, s: int) -> bool:
    """Whether the k-group and j-group have at least s common elements."""
    return (k_mask & j_mask).bit_count() >= s


# -----------------------------
# 3) Build targets and candidates
# -----------------------------
def build_target_masks(samples: Sequence[int], j: int) -> List[int]:
    return [to_mask(g) for g in combinations(samples, j)]


def build_candidate_groups(
    samples: Sequence[int],
    k: int,
    max_candidates: int = 200000,
    seed: int = 42,
) -> Tuple[List[Tuple[int, ...]], List[int], bool, int]:
    """
    If the number of all k-combinations is small enough, use all of them.
    Otherwise, build a candidate pool with a simple heuristic.
    """
    samples = tuple(sorted(samples))
    total_count = comb(len(samples), k)

    if total_count <= max_candidates:
        candidate_groups = list(combinations(samples, k))
        candidate_masks = [to_mask(g) for g in candidate_groups]
        return candidate_groups, candidate_masks, False, total_count

    rng = random.Random(seed)
    candidate_pool = set()
    n = len(samples)

    # Add some consecutive groups first
    for start in range(max(1, n - k + 1)):
        candidate_pool.add(tuple(samples[start:start + k]))
        if len(candidate_pool) >= max_candidates:
            break

    # Fill the rest randomly
    while len(candidate_pool) < max_candidates:
        candidate_pool.add(tuple(sorted(rng.sample(samples, k))))

    candidate_groups = list(candidate_pool)
    candidate_masks = [to_mask(g) for g in candidate_groups]
    return candidate_groups, candidate_masks, True, total_count


# -----------------------------
# 4) Precompute coverage information
# -----------------------------
def build_cover_bits(
    candidate_groups: List[Tuple[int, ...]],
    candidate_masks: List[int],
    target_masks: List[int],
    s: int,
    j: int,
) -> List[int]:
    """
    Build coverage information for each candidate.

    Normal case:
        Check each candidate against each target.

    Faster case when s == j:
        A target is covered only if all its j elements are inside the candidate.
        So we only need to generate j-combinations inside each candidate.
    """

    # Fast path: when s == j, target must be a subset of candidate
    if s == j:
        target_index = {mask: idx for idx, mask in enumerate(target_masks)}
        cover_bits = []

        for group in candidate_groups:
            bits = 0

            # Only generate target groups that are inside this candidate
            for sub_group in combinations(group, j):
                sub_mask = to_mask(sub_group)
                idx = target_index.get(sub_mask)

                if idx is not None:
                    bits |= 1 << idx

            cover_bits.append(bits)

        return cover_bits

    # General case
    cover_bits = []
    for k_mask in candidate_masks:
        bits = 0
        for t_idx, t_mask in enumerate(target_masks):
            if is_covered_mask(k_mask, t_mask, s):
                bits |= 1 << t_idx
        cover_bits.append(bits)

    return cover_bits


# -----------------------------
# 5) Greedy + pruning
# -----------------------------
def greedy_once(
    cover_bits: List[int],
    target_count: int,
    candidate_order: List[int],
) -> Tuple[List[int], int]:
    """Run greedy once under a given candidate order."""
    uncovered_bits = (1 << target_count) - 1
    selected_indices: List[int] = []
    selected_set = set()

    # Used later in pruning: how many times each target is covered
    cover_count = [0] * target_count

    # Step 1: greedy selection
    while uncovered_bits:
        best_idx = -1
        best_new_cover = 0
        best_new_count = 0

        for idx in candidate_order:
            if idx in selected_set:
                continue

            new_cover = cover_bits[idx] & uncovered_bits
            new_count = new_cover.bit_count()

            if new_count > best_new_count:
                best_idx = idx
                best_new_cover = new_cover
                best_new_count = new_count

                if best_new_count == uncovered_bits.bit_count():
                    break

        if best_idx == -1:
            break

        selected_indices.append(best_idx)
        selected_set.add(best_idx)
        uncovered_bits &= ~best_new_cover

        bits = cover_bits[best_idx]
        for t_idx in range(target_count):
            if (bits >> t_idx) & 1:
                cover_count[t_idx] += 1

    # Step 2: remove obviously redundant groups
    pruned_indices: List[int] = []
    for idx in selected_indices:
        bits = cover_bits[idx]
        removable = True

        for t_idx in range(target_count):
            if ((bits >> t_idx) & 1) and cover_count[t_idx] <= 1:
                removable = False
                break

        if removable:
            for t_idx in range(target_count):
                if (bits >> t_idx) & 1:
                    cover_count[t_idx] -= 1
        else:
            pruned_indices.append(idx)

    return pruned_indices, uncovered_bits.bit_count()


def multi_start_greedy(
    cover_bits: List[int],
    target_count: int,
    attempts: int = 3,
    seed: int = 42,
) -> Tuple[List[int], int]:
    """
    Run greedy several times with different orders.
    We first prefer fewer uncovered targets, then fewer groups.
    """
    rng = random.Random(seed)
    base_order = list(range(len(cover_bits)))

    best_indices: List[int] = []
    best_uncovered = float("inf")
    best_group_count = float("inf")

    for attempt in range(attempts):
        current_order = base_order[:]
        if attempt > 0:
            rng.shuffle(current_order)

        indices, uncovered = greedy_once(cover_bits, target_count, current_order)

        if uncovered < best_uncovered or (
            uncovered == best_uncovered and len(indices) < best_group_count
        ):
            best_indices = indices
            best_uncovered = uncovered
            best_group_count = len(indices)

        if best_uncovered == 0 and best_group_count <= 1:
            break

    return best_indices, int(best_uncovered)


# -----------------------------
# 6) Main interface
# -----------------------------
def solve(
    samples: Sequence[int],
    m: int,
    n: int,
    k: int,
    j: int,
    s: int,
    max_candidates: int = 200000,
    seed: int = 42,
    attempts: int = 3,
) -> Dict[str, Any]:
    start = time.perf_counter()

    ok, msg = check_parameters(m, n, k, j, s)
    if not ok:
        return {
            "status": "error",
            "message": msg,
            "input": {"m": m, "n": n, "k": k, "j": j, "s": s},
        }

    ok, msg = check_samples(samples, m, n)
    if not ok:
        return {
            "status": "error",
            "message": msg,
            "input": {"m": m, "n": n, "k": k, "j": j, "s": s},
        }

    samples = sorted(list(samples))
        # Special case:
    # If j == k == s, a target can only be covered by exactly the same group.
    # So the best solution is simply all k-groups.
    if j == k == s:
        selected_groups = list(combinations(samples, k))
        runtime_ms = round((time.perf_counter() - start) * 1000, 2)

        return {
            "status": "ok",
            "message": "Success (special case: j = k = s)",
            "input": {"m": m, "n": n, "k": k, "j": j, "s": s},
            "samples": samples,
            "selected_groups": selected_groups,
            "group_count": len(selected_groups),
            "is_valid": True,
            "runtime_ms": runtime_ms,
            "target_count": len(selected_groups),
            "candidate_count_used": len(selected_groups),
            "candidate_count_total": len(selected_groups),
            "mode": "special-case",
            "uncovered_target_count": 0,
            "attempts_used": 0,
        }

    target_masks = build_target_masks(samples, j)
    target_count = len(target_masks)

    candidate_groups, candidate_masks, heuristic_used, total_candidate_count = build_candidate_groups(
        samples=samples,
        k=k,
        max_candidates=max_candidates,
        seed=seed,
    )

    cover_bits = build_cover_bits(
    candidate_groups=candidate_groups,
    candidate_masks=candidate_masks,
    target_masks=target_masks,
    s=s,
    j=j,
)
    
    # For large cases, running greedy multiple times can be slow.
    # So we reduce attempts automatically to keep the program responsive.
    workload = len(candidate_groups) * target_count
    effective_attempts = attempts

    if workload > 30_000_000:
        effective_attempts = 1

    selected_indices, uncovered_count = multi_start_greedy(
        cover_bits=cover_bits,
        target_count=target_count,
        attempts=effective_attempts,
        seed=seed,
    )

    selected_groups = [candidate_groups[i] for i in selected_indices]

    is_valid = False
    if uncovered_count == 0:
        final_bits = 0
        for i in selected_indices:
            final_bits |= cover_bits[i]
        is_valid = final_bits == (1 << target_count) - 1

    runtime_ms = round((time.perf_counter() - start) * 1000, 2)

    mode = "heuristic" if heuristic_used else "full-candidate"
    status = "ok" if is_valid else "partial"
    if is_valid:
        message = f"Success ({mode} mode)"
    else:
        message = f"Incomplete coverage ({mode} mode)"

    return {
        "status": status,
        "message": message,
        "input": {"m": m, "n": n, "k": k, "j": j, "s": s},
        "samples": samples,
        "selected_groups": selected_groups,
        "group_count": len(selected_groups),
        "is_valid": is_valid,
        "runtime_ms": runtime_ms,
        "target_count": target_count,
        "candidate_count_used": len(candidate_groups),
        "candidate_count_total": total_candidate_count,
        "mode": mode,
        "uncovered_target_count": uncovered_count,
        "attempts_used": effective_attempts,
    }


# -----------------------------
# 7) Simple test
# -----------------------------
if __name__ == "__main__":
    from pprint import pprint

    # Example from the report / notes
    samples = [1, 5, 12, 18, 22, 30, 41]
    result = solve(
        samples=samples,
        m=45,
        n=7,
        k=4,
        j=4,
        s=3,
    )

    pprint(result)
