from functools import partial

import numpy as np
from IPython.core.display import clear_output

from taped.scrap.live_audio import launch_audio_tracking
from taped.util import find_a_default_input_device_index

from lined.tools import iterize
from lined import Pipeline

int16_max = np.iinfo(np.int16).max


def log_max_chk_to_fv(chk: np.ndarray, gain=50):
    """A chk_to_fv that has to do with volume"""
    return [np.log(max(chk.max(), abs(chk.min()), 1)) / np.log(int16_max) * gain]
    # return np.log(min(1, max(np.abs(chk)))) / np.log(int16_max) * gain


dflt_chk_to_fv = log_max_chk_to_fv


def ap_fv_to_viz(fv):
    return f'/><{r"{" * int(sum(fv))}">'


dflt_fv_to_viz = ap_fv_to_viz


def ap_chk_to_viz(chk: np.ndarray, gain=50):
    return ap_fv_to_viz(log_max_chk_to_fv(chk, gain))


dflt_chk_to_viz = ap_chk_to_viz


class DFLT:
    gain = 10
    cutoff = 50
    dispstr = "*"
    prefix = "|"
    fv_num_sep = "\n"


def viz_norm(x, gain=10, cutoff=50):
    return min(cutoff, x * gain)


def ascii_levels(x, viz_norm=viz_norm, dispstr=DFLT.dispstr, prefix=DFLT.prefix):
    return prefix + dispstr * int(viz_norm(x))


dflt_num_to_viz_str = ascii_levels


def multipart_fv_str(
    fv, num_to_viz_str=dflt_num_to_viz_str, fv_num_sep=DFLT.fv_num_sep
):
    return fv_num_sep.join(map(num_to_viz_str, fv)) + "\n"


ascii_levels_fv_to_str = partial(
    multipart_fv_str, num_to_viz_str=ascii_levels, fv_num_sep=DFLT.fv_num_sep
)

raw_fv_to_str = partial(
    multipart_fv_str, num_to_viz_str=str, fv_num_sep=DFLT.fv_num_sep
)

dflt_fv_to_str = ascii_levels_fv_to_str


def chk_to_fv_viz(chk: np.ndarray, chk_to_fv=dflt_chk_to_fv, fv_to_str=dflt_fv_to_str):
    """Takes a chk and returns a string representing the fv. Meant to be displayed dynamically"""
    fv = chk_to_fv(chk)
    fv_str = fv_to_str(fv)
    return fv_str


def refresh_and_print(iterator_output):
    clear_output(wait=True)
    n, viz = iterator_output
    print(n, viz, sep="\n")


from collections import deque


class CallableDeque(deque):
    def __call__(self, x):
        self.append(x)


dflt_output_callback = refresh_and_print


def make_and_consume_iterator(
    iterator_func, *iterator_func_args, **iterator_func_kwargs
):
    """make an consume and iterator"""
    for _ in iterator_func(*iterator_func_args, **iterator_func_kwargs):
        pass


def mk_launcher(
    chk_to_fv=dflt_chk_to_fv,
    fv_to_viz=dflt_fv_to_viz,
    input_device_index=None,
    output_callback=dflt_output_callback,
):
    if input_device_index is None:
        input_device_index = find_a_default_input_device_index()

    def chk_to_fv_viz(chk):
        return fv_to_viz(chk_to_fv(chk))

    pipe = Pipeline(launch_audio_tracking, iterize(output_callback))

    def launch():
        make_and_consume_iterator(
            pipe, chk_callback=chk_to_fv_viz, input_device_index=input_device_index
        )

    return launch
