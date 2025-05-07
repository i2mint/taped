"""This is a first draft to get some functions to estimate sample rate
bias and drift.

Consider that functions might have to be written that are closer to the microphone to
get more accurate estimates.

"""

import os
from itertools import islice
from functools import partial
from typing import Sequence, MutableMapping, Union
from time import time
import pickle
import json
from pathlib import Path

import taped
from lkj import get_watermarked_dir
from slang import fixed_step_chunker
from dol import Files, wrap_kvs, Pipe

# import pandas as pd


def gather_sample_rate_date(
    chk_size=20000,
    sr=20_000,
    n_chks=10,
    input_device_index=None,
    read_chk_size=4096,
    *,
    display_input_device_info_when_not_chosen=False,
):
    """"""
    chunker = partial(fixed_step_chunker, chk_size=chk_size)
    wf = taped.LiveWf(
        input_device_index=input_device_index, sr=sr, chk_size=read_chk_size
    )
    with wf:

        def gen():
            chks = iter(islice(chunker(wf), n_chks))
            while True:
                try:
                    yield {"bt": time(), "n_samples": len(next(chks)), "tt": time()}
                except StopIteration:
                    break

        data = list(gen())

    return data


def params_to_key(params: dict, ext="") -> str:
    """Convert a dict of parameters to a key for a dict-like object

    >>> params_to_key({'a': 1, 'b': 2})
    'a=1,b=2'
    >>> params_to_key({'b': 2, 'a': 1}, ext='.csv')
    'a=1,b=2.csv'
    """
    return ",".join(f"{k}={params[k]}" for k in sorted(params)) + ext


def key_to_params(key: str):
    """Convert a key to a dict of parameters. Approximate inverse of params_to_key

    >>> key_to_params('a=1,b=2')
    {'a': '1', 'b': '2'}
    >>> key_to_params('b=2,a=1.csv')
    {'a': '1', 'b': '2'}
    """
    key, _ = os.path.splitext(key)  # remove the extension if present
    kvs = (kv.split("=") for kv in key.split(","))
    return dict(kv for kv in sorted(kvs, key=lambda x: x[0]))


dflt_store_folder = get_watermarked_dir(
    "taped/sample_rate_bias", make_dir=partial(os.makedirs, exist_ok=True)
)
dflt_params_folder = os.path.join(dflt_store_folder, "params")
JsonFiles = wrap_kvs(
    Files, data_of_obj=Pipe(json.dumps, str.encode), obj_of_data=json.loads
)
dflt_store = JsonFiles(dflt_store_folder, max_levels=0)

import itertools

list(itertools.product([1, 2], [4, 5, 6]))

IntList = Sequence[int]


def load_json(filepath: str) -> dict:
    return json.loads(Path(filepath).read_text())


def save_json(filepath: str, data: Union[dict, list]):
    Path(filepath).write_text(json.dumps(data))


def params_product(
    save_to_filepath: str = None,
    *,
    chk_size: IntList = (20_000,),
    sr: IntList = (20_000,),
    n_chks: IntList = (30,),
    read_chk_size: IntList = (4096,),
):
    """To create a list of parameters to pass to run_experiments"""
    params = [
        dict(zip(("chk_size", "sr", "n_chks", "read_chk_size"), p))
        for p in itertools.product(chk_size, sr, n_chks, read_chk_size)
    ]
    if save_to_filepath:
        save_json(save_to_filepath, params)


def _get_params_list(params_list: Union[str, Sequence[dict]]) -> Sequence[dict]:
    if isinstance(params_list, str):
        import json
        from pathlib import Path

        filepath = params_list
        if not os.path.exists(filepath):
            filepath = os.path.join(dflt_params_folder, filepath)

        params_list = json.loads(Path(filepath).read_text())
    return params_list


def _get_store(store: Union[str, MutableMapping] = dflt_store) -> MutableMapping:
    if isinstance(store, str):
        filepath = store
        store = JsonFiles(filepath)
    return store


def run_experiments(
    params_list: Union[str, Sequence[dict]],
    store: Union[str, MutableMapping] = dflt_store,
    *,
    print_progress=True,
    overwrite: bool = False,
):
    params_list = _get_params_list(params_list)
    store = _get_store(store)
    n = len(list(params_list))
    for i, params in enumerate(params_list, 1):
        key = params_to_key(params)
        if key in store and not overwrite:
            continue  # skip this one, we have it already
        print_progress and print(f"{i}/{n}: {key}")
        store[key] = gather_sample_rate_date(**params)
    return store


def observed_sample_rates(d):
    import pandas as pd

    df = pd.DataFrame(d)
    return df["n_samples"] / (df["tt"] - df["bt"])


def observed_sample_rates_plot(k, v):
    import pandas as pd

    df = pd.DataFrame(v)
    df = df["n_samples"] / (df["tt"] - df["bt"])
    return df.plot(title=k, marker="o", linestyle="-")


def mk_df_store(store):
    return wrap_kvs(store, obj_of_data=observed_sample_rates)


def mk_plot_store(store):
    return wrap_kvs(store, postget=observed_sample_rates_plot)


if __name__ == "__main__":
    import argh

    argh.dispatch_command(run_experiments)
