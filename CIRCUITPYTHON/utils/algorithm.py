def peak_detect(array: list, threshold: float, window_size: int) -> int:
    moving_sum = sum(array[:window_size - 1])
    global_max_val = 0
    global_max_ind = -1
    for i in range(window_size - 1, len(array)):
        current_val = array[i]
        if current_val > global_max_val:
            global_max_val = current_val
            global_max_ind = i
        moving_sum += current_val
        if current_val < array[i - 1] < array[i - 2]:
            # Last two points have both decreased
            if moving_sum / window_size - current_val > threshold:
                return global_max_ind
        moving_sum -= array[i - (window_size - 1)]
    else:
        return None
