import random
import time
from itertools import combinations
from math import comb
from typing import Any, Dict, List, Sequence, Tuple


# check
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


# mask
def to_mask(group: Sequence[int]) -> int:
    mask = 0
    for x in group:
        mask |= 1 << (x - 1)
    return mask


# generate candidates
def build_candidate_groups(
    samples: Sequence[int],
    k: int,
    max_candidates: int = 100000,
    seed: int = 42,
) -> Tuple[List[Tuple[int, ...]], bool, int]:
    samples = tuple(sorted(samples))
    total_count = comb(len(samples), k)

    if total_count <= max_candidates:
        return list(combinations(samples, k)), False, total_count

    rng = random.Random(seed)
    candidate_pool = set()
    n = len(samples)

    for start in range(max(1, n - k + 1)):
        candidate_pool.add(tuple(samples[start:start + k]))
        if len(candidate_pool) >= max_candidates:
            break

    while len(candidate_pool) < max_candidates:
        candidate_pool.add(tuple(sorted(rng.sample(samples, k))))

    return list(candidate_pool), True, total_count


# build coverage relations
def build_coverage_graph(
    candidate_groups: List[Tuple[int, ...]],
    target_masks: List[int],
    samples: Sequence[int],
    k: int,
    j: int,
    s: int,
) -> Tuple[List[List[int]], List[List[int]]]:
    target_index = {mask: idx for idx, mask in enumerate(target_masks)}

    cand_count = len(candidate_groups)
    target_count = len(target_masks)

    cand_to_targets = [[] for _ in range(cand_count)]
    target_to_cands = [[] for _ in range(target_count)]

    samples_set = set(samples)

    for c_idx, group in enumerate(candidate_groups):
        group_set = set(group)
        outside = sorted(list(samples_set - group_set))

        for intersect_size in range(s, min(j, k) + 1):
            if j - intersect_size > len(outside):
                continue

            for core in combinations(group, intersect_size):
                core_mask = to_mask(core)
                for extra in combinations(outside, j - intersect_size):
                    t_mask = core_mask | to_mask(extra)
                    t_idx = target_index.get(t_mask)
                    if t_idx is not None:
                        cand_to_targets[c_idx].append(t_idx)
                        target_to_cands[t_idx].append(c_idx)

    return cand_to_targets, target_to_cands


# greedy
def greedy_bucket_solver(
    cand_to_targets: List[List[int]],
    target_to_cands: List[List[int]],
    target_count: int,
) -> Tuple[List[int], int]:
    scores = [len(targets) for targets in cand_to_targets]
    max_score = max(scores) if scores else 0

    buckets = [set() for _ in range(max_score + 1)]
    for c, score in enumerate(scores):
        buckets[score].add(c)

    covered_targets = bytearray(target_count)
    selected = []
    selected_set = set()

    # greedy
    while max_score > 0:
        if not buckets[max_score]:
            max_score -= 1
            continue

        c = buckets[max_score].pop()
        selected.append(c)
        selected_set.add(c)

        for t in cand_to_targets[c]:
            if not covered_targets[t]:
                covered_targets[t] = 1

                for other_c in target_to_cands[t]:
                    if other_c not in selected_set:
                        old_score = scores[other_c]
                        buckets[old_score].remove(other_c)
                        scores[other_c] -= 1
                        buckets[old_score - 1].add(other_c)

    uncovered_count = target_count - sum(covered_targets)

    # pruning
    cover_counts = [0] * target_count
    for c in selected:
        for t in cand_to_targets[c]:
            cover_counts[t] += 1

    pruned_indices = []
    for c in selected:
        removable = True
        for t in cand_to_targets[c]:
            if cover_counts[t] <= 1:
                removable = False
                break
        if removable:
            for t in cand_to_targets[c]:
                cover_counts[t] -= 1
        else:
            pruned_indices.append(c)

    return pruned_indices, uncovered_count


# solve
def solve(
    samples: Sequence[int],
    m: int,
    n: int,
    k: int,
    j: int,
    s: int,
    max_candidates: int = 100000,
    seed: int = 42,
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

    if j == k == s:
        selected_groups = list(combinations(samples, k))
        return {
            "status": "ok",
            "message": "Success (special case)",
            "selected_groups": selected_groups,
            "group_count": len(selected_groups),
            "is_valid": True,
            "runtime_ms": round((time.perf_counter() - start) * 1000, 2),
            "target_count": len(selected_groups),
            "uncovered_target_count": 0,
        }

    target_groups = list(combinations(samples, j))
    target_masks = [to_mask(g) for g in target_groups]
    target_count = len(target_masks)

    candidate_groups, heuristic_used, total_cands = build_candidate_groups(
        samples=samples,
        k=k,
        max_candidates=max_candidates,
        seed=seed,
    )

    cand_to_targets, target_to_cands = build_coverage_graph(
        candidate_groups,
        target_masks,
        samples,
        k,
        j,
        s,
    )

    selected_indices, uncovered_count = greedy_bucket_solver(
        cand_to_targets,
        target_to_cands,
        target_count,
    )

    selected_groups = [candidate_groups[i] for i in selected_indices]
    is_valid = uncovered_count == 0

    runtime_ms = round((time.perf_counter() - start) * 1000, 2)
    mode = "heuristic" if heuristic_used else "exact"
    status = "ok" if is_valid else "partial"
    message = f"Success ({mode} mode)" if is_valid else f"Incomplete coverage ({mode} mode)"

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
        "candidate_count_total": total_cands,
        "mode": mode,
        "uncovered_target_count": uncovered_count,
    }


if __name__ == "__main__":
    print("test 1")
    res_1 = solve(samples=[1, 2, 3, 4, 5, 6, 7], m=45, n=7, k=6, j=5, s=5)
    print(f"group count: {res_1['group_count']} | valid: {res_1['is_valid']} | time: {res_1['runtime_ms']} ms")

    print("test 2")
    res_2 = solve(samples=[1, 2, 3, 4, 5, 6, 7, 8], m=45, n=8, k=6, j=5, s=5)
    print(f"group count: {res_2['group_count']} | valid: {res_2['is_valid']} | time: {res_2['runtime_ms']} ms")

    print("test 3")
    samples_25 = list(range(1, 26))
    res_limit = solve(samples=samples_25, m=45, n=25, k=7, j=6, s=5, max_candidates=100000)
    print(f"status: {res_limit['message']}")
    print(f"targets: {res_limit['target_count']}")
    print(f"group count: {res_limit['group_count']}")
    print(f"valid: {res_limit['is_valid']}")
    print(f"time: {res_limit['runtime_ms']} ms")