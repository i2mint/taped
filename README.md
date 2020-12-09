
# taped
Python's serene audio accessor


To install:	```pip install taped```


# Example

Gives you access to your microphone as an iterator of numerical samples.

```pydocstring
>>> from itertools import islice
>>> from taped import live_wf_ctx
>>>
>>> with live_wf_ctx() as live_audio_stream:
...     first_sample = next(live_audio_stream)  # get a sample
...     second_sample = next(live_audio_stream)  # get the next sample
...     ten_samples = list(islice(live_audio_stream, 7))  # get the next 7 samples
...     a_3_6_slice = list(islice(live_audio_stream, 3, 6))  # skip 3 samples and
...     downsampled = list(islice(live_audio_stream, 0, 10, 2))  # take every other sample (i.e. down-sampling)
>>>
>>> first_sample
-323
>>> second_sample
-1022
>>> ten_samples
[-1343, -1547, -1687, -1651, -1623, -1511, -1449]
>>> a_3_6_slice
[-1323, -1322, -1274]
>>> downsampled
[-1263, -1272, -1220, -1192, -1168]
```

From there, the sky is the limit.

```pydocstring
from hum import disp_wf

```
