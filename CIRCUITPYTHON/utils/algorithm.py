def peak_detect(array: list, threshold: float, window_size: int) -> int:
    moving_sum = sum(array[:window_size - 1])
    global_max_val = 0
    global_max_ind = -1
    peak_candidate_ind = None
    peak_candidate_val = None
    for i in range(window_size - 1, len(array)):
        current_val = array[i]
        if current_val > global_max_val:
            global_max_val = current_val
            global_max_ind = i
            if peak_candidate_val is not None and global_max_val > peak_candidate_val:
                peak_candidate_ind = None
                peak_candidate_val = None
        moving_sum += current_val
        if current_val < array[i - 1] < array[i - 2]:
            # Last two points have both decreased
            if moving_sum / window_size - current_val > threshold:
                peak_candidate_ind = global_max_ind
                peak_candidate_val = global_max_val
        moving_sum -= array[i - (window_size - 1)]
    return peak_candidate_ind
