from itertools import combinations
from math import comb
import random
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple


# -----------------------------
# input checks
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
        return False, "n must be greater than or equal to k"
    return True, "Parameters are valid"


def check_samples(samples: Sequence[int], m: int, n: int) -> Tuple[bool, str]:
    if not isinstance(samples, (list, tuple)):
        return False, "samples must be a list or tuple"
    if len(samples) != n:
        return False, "the number of samples must be equal to n"
    if len(set(samples)) != n:
        return False, "duplicate values are not allowed"
    if any(not isinstance(x, int) for x in samples):
        return False, "all samples must be integers"
    if any(x < 1 or x > m for x in samples):
        return False, "samples must be within 1..m"
    return True, "Samples are valid"


# -----------------------------
# helpers
# -----------------------------
def to_mask(group: Sequence[int]) -> int:
    mask = 0
    for x in group:
        mask |= 1 << (x - 1)
    return mask


def iter_bits(bits: int):
    while bits:
        low = bits & -bits
        yield low.bit_length() - 1
        bits ^= low


def make_result(
    status: str,
    message: str,
    samples: List[int],
    m: int,
    n: int,
    k: int,
    j: int,
    s: int,
    selected_groups: List[Tuple[int, ...]],
    is_valid: bool,
    runtime_ms: float,
    target_count: int,
    candidate_count_used: int,
    candidate_count_total: int,
    mode: str,
    uncovered_target_count: int,
    heuristic_used: bool,
) -> Dict[str, Any]:
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
        "candidate_count_used": candidate_count_used,
        "candidate_count_total": candidate_count_total,
        "mode": mode,
        "heuristic_candidate_pool": heuristic_used,
        "uncovered_target_count": uncovered_target_count,
    }


# -----------------------------
# fast shortcuts
# -----------------------------
def shortcut_solution(samples: List[int], k: int, j: int, s: int) -> Optional[Tuple[str, List[Tuple[int, ...]]]]:
    n = len(samples)

    # Any k-group must share at least s elements with any j-group.
    if k + j - n >= s:
        return "shortcut-one-group", [tuple(samples[:k])]

    # In this case, a group only covers itself.
    if j == k == s:
        return "shortcut-identical", list(combinations(samples, k))

    return None


# -----------------------------
# exact greedy, only for small cases
# -----------------------------
def build_target_index(samples: List[int], j: int, s: int) -> Tuple[Dict[int, int], int]:
    sub_to_targets: Dict[int, int] = {}
    target_count = 0

    for target in combinations(samples, j):
        bit = 1 << target_count
        for sub in combinations(target, s):
            sub_mask = to_mask(sub)
            sub_to_targets[sub_mask] = sub_to_targets.get(sub_mask, 0) | bit
        target_count += 1

    return sub_to_targets, target_count


def candidate_cover_bits(group: Tuple[int, ...], sub_to_targets: Dict[int, int], s: int) -> int:
    bits = 0
    for sub in combinations(group, s):
        bits |= sub_to_targets.get(to_mask(sub), 0)
    return bits


def greedy_once(cover_bits: List[int], target_count: int, order: List[int]) -> Tuple[List[int], int]:
    uncovered = (1 << target_count) - 1
    selected: List[int] = []
    selected_set = set()

    while uncovered:
        best_idx = -1
        best_gain = 0
        best_bits = 0
        left_count = uncovered.bit_count()

        for idx in order:
            if idx in selected_set:
                continue
            new_bits = cover_bits[idx] & uncovered
            gain = new_bits.bit_count()
            if gain > best_gain:
                best_idx = idx
                best_gain = gain
                best_bits = new_bits
                if gain == left_count:
                    break

        if best_idx < 0 or best_gain == 0:
            break

        selected.append(best_idx)
        selected_set.add(best_idx)
        uncovered &= ~best_bits

    return selected, uncovered.bit_count()


def prune_small(selected: List[int], cover_bits: List[int], target_count: int) -> List[int]:
    if not selected:
        return selected

    counts = [0] * target_count
    for idx in selected:
        for t in iter_bits(cover_bits[idx]):
            counts[t] += 1

    kept: List[int] = []
    for idx in selected:
        bits = cover_bits[idx]
        removable = True
        for t in iter_bits(bits):
            if counts[t] <= 1:
                removable = False
                break
        if removable:
            for t in iter_bits(bits):
                counts[t] -= 1
        else:
            kept.append(idx)

    return kept


def exact_greedy_solver(
    samples: List[int],
    k: int,
    j: int,
    s: int,
    attempts: int,
    seed: int,
) -> Tuple[List[Tuple[int, ...]], bool, int, int, str]:
    sub_to_targets, target_count = build_target_index(samples, j, s)
    candidate_groups = list(combinations(samples, k))
    cover_bits = [candidate_cover_bits(g, sub_to_targets, s) for g in candidate_groups]

    rng = random.Random(seed)
    base_order = list(range(len(candidate_groups)))
    best_selected: List[int] = []
    best_uncovered = target_count + 1
    best_count = 10**18

    run_times = max(1, attempts)
    for a in range(run_times):
        order = base_order[:]
        if a > 0:
            rng.shuffle(order)

        selected, uncovered = greedy_once(cover_bits, target_count, order)
        selected = prune_small(selected, cover_bits, target_count)

        final_bits = 0
        for idx in selected:
            final_bits |= cover_bits[idx]
        uncovered = target_count - final_bits.bit_count()

        if uncovered < best_uncovered or (uncovered == best_uncovered and len(selected) < best_count):
            best_selected = selected
            best_uncovered = uncovered
            best_count = len(selected)

        if best_uncovered == 0 and a >= 1:
            break

    selected_groups = [candidate_groups[i] for i in best_selected]
    return selected_groups, best_uncovered == 0, best_uncovered, len(candidate_groups), "exact-greedy"


# -----------------------------
# large case: cover all s-subsets directly
# -----------------------------
def extend_subset_to_k_group(sub: Tuple[int, ...], samples: List[int], k: int) -> Tuple[int, ...]:
    n = len(samples)
    pos = {x: i for i, x in enumerate(samples)}
    idxs = [pos[x] for x in sub]
    lo = min(idxs)
    hi = max(idxs)

    # Try a nearby k-window first. This reduces duplicate-free groups a bit.
    if hi - lo + 1 <= k:
        start_low = max(0, hi - k + 1)
        start_high = min(lo, n - k)
        start = start_low if start_low <= start_high else max(0, min(lo, n - k))
        return tuple(samples[start:start + k])

    # If the subset is spread out, add the first available elements.
    used = set(sub)
    group = list(sub)
    for x in samples:
        if x not in used:
            group.append(x)
            used.add(x)
            if len(group) == k:
                break

    return tuple(sorted(group))


def s_subset_direct_solver(
    samples: List[int],
    k: int,
    j: int,
    s: int,
) -> Tuple[List[Tuple[int, ...]], bool, int, int, str]:
    selected_set = set()

    for sub in combinations(samples, s):
        g = extend_subset_to_k_group(sub, samples, k)
        selected_set.add(g)

    selected_groups = sorted(selected_set)

    # Covering every s-subset guarantees every j-group is covered.
    return selected_groups, True, 0, len(selected_groups), "s-subset-direct"


# -----------------------------
# main API
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
    attempts: int = 2,
    exact_work_limit: int = 50_000_000,
    exact_candidate_limit: int = 10000,
) -> Dict[str, Any]:
    start = time.perf_counter()

    ok, msg = check_parameters(m, n, k, j, s)
    if not ok:
        return {"status": "error", "message": msg, "input": {"m": m, "n": n, "k": k, "j": j, "s": s}}

    ok, msg = check_samples(samples, m, n)
    if not ok:
        return {"status": "error", "message": msg, "input": {"m": m, "n": n, "k": k, "j": j, "s": s}}

    samples = sorted(list(samples))
    target_count = comb(n, j)
    candidate_total = comb(n, k)

    shortcut = shortcut_solution(samples, k, j, s)
    if shortcut is not None:
        mode, selected_groups = shortcut
        runtime_ms = round((time.perf_counter() - start) * 1000, 2)
        return make_result(
            "ok", f"Success ({mode})",
            samples, m, n, k, j, s,
            selected_groups, True, runtime_ms,
            target_count, len(selected_groups), candidate_total,
            mode, 0, mode != "exact-greedy",
        )

    estimated_work = target_count * candidate_total

    # Keep greedy only for truly small cases.
    use_exact = candidate_total <= exact_candidate_limit and estimated_work <= exact_work_limit

    if use_exact:
        selected_groups, is_valid, uncovered, used, mode = exact_greedy_solver(
            samples, k, j, s, max(1, attempts), seed
        )
        heuristic = False
    else:
        selected_groups, is_valid, uncovered, used, mode = s_subset_direct_solver(
            samples, k, j, s
        )
        heuristic = True

    status = "ok" if is_valid else "partial"
    message = f"Success ({mode})" if is_valid else f"Incomplete coverage ({mode})"
    runtime_ms = round((time.perf_counter() - start) * 1000, 2)

    return make_result(
        status, message,
        samples, m, n, k, j, s,
        selected_groups, is_valid, runtime_ms,
        target_count, used, candidate_total,
        mode, uncovered, heuristic,
    )


if __name__ == "__main__":
    tests = [
        (50, 12, 6, 5, 3),
        (50, 15, 7, 6, 5),
        (50, 20, 7, 6, 5),
        (50, 25, 7, 6, 5),
    ]
    for m, n, k, j, s in tests:
        r = solve(list(range(1, n + 1)), m, n, k, j, s)
        print((n, k, j, s), r["mode"], r["status"], r["group_count"], r["runtime_ms"])
