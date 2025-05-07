from itertools import islice
from functools import partial
from statistics import pstdev
import pickle
import os

from i2.signatures import Sig
from lined import Pipeline, iterize, iterate

from taped.util import wraps
from taped import LiveWf, simple_chunker


def std(x):
    """Wrapping statistics.pstdev, so it doesn't cause issues such as https://bugs.python.org/issue39218"""
    return pstdev(map(float, x))


def mk_pipeline(
    chunker=partial(simple_chunker, chk_size=2048), model=pstdev, output_func=print
):
    if isinstance(chunker, int):
        chk_size = chunker
        chunker = partial(simple_chunker, chk_size=chk_size)
    return Pipeline(chunker, iterize(model), iterize(output_func), iterate)


def launch(pipeline=None, max_samples=20000):
    if pipeline is None:
        pipeline = mk_pipeline()
    try:
        with LiveWf() as live_wf:
            if max_samples:
                wf = islice(live_wf, 0, max_samples)
            else:
                wf = live_wf
            pipeline(wf)
    except KeyboardInterrupt:
        print("A KeyboardInterrupt was received. Closing down...")


def viz(val, gain=1 / 20, offset=0, disp_str="*"):
    print(disp_str * int(gain * val + offset))


def _unpickle_if_filepath(obj):
    if isinstance(obj, str) and os.path.isfile(obj):
        filepath = obj
        with open(filepath, "r") as f:
            obj = pickle.load(f)
    return obj


def strings_as_pickle_files(func):
    @wraps(func)
    def _func(*args, **kwargs):
        _args = tuple(map(_unpickle_if_filepath, args))
        _kwargs = {k: _unpickle_if_filepath(v) for k, v in kwargs.items()}
        return func(*_args, **_kwargs)

    return _func


# Pattern: TODO: Use general input_trans pattern
@strings_as_pickle_files
@wraps(mk_pipeline)
def main(*args, **kwargs):
    max_samples = kwargs.pop(
        "max_samples", None
    )  # this argument will be hidden (use Sig to add it to signature?)
    kwargs = Sig(mk_pipeline).extract_kwargs(*args, **kwargs)
    if "chunker" in kwargs and str.isnumeric(kwargs["chunker"]):
        kwargs["chunker"] = int(kwargs["chunker"])
    pipeline = mk_pipeline(**kwargs)

    return launch(pipeline, max_samples=max_samples)


if __name__ == "__main__":
    import argh
    from inspect import signature

    argh.dispatch_command(main)
    # argh.dispatch_command(main, argv=list(signature(mk_pipeline).parameters))
