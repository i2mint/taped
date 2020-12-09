
# taped
Python's serene audio accessor


To install:	```pip install taped```


# Basically...

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

For instance...

## Record and display audio from a microphone

```python
from taped import live_wf_ctx, disp_wf


def record_and_display_audio_from_microphone(n_samples=10000, sample_rate=22050):
    with live_wf_ctx(sr=sample_rate) as live_audio_stream:
        wf = list(islice(live_audio_stream, n_samples))
    return disp_wf(wf, sample_rate)

record_and_display_audio_from_microphone()
```

![image](https://user-images.githubusercontent.com/1906276/101562916-289cec00-397d-11eb-8a40-d3a7345e40da.png)


## Record and save audio from microphone

```python
from taped import live_wf_ctx, disp_wf
import soundfile as sf  # pip install soundfile (or get your waveform_to_file function elsewhere)

def record_and_save_audio_from_microphone(filepath='tmp.wav', n_samples=10000, sample_rate=22050):
    with live_wf_ctx(0, sr=sample_rate) as live_audio_stream:
        sf.write(filepath, 
                 data=list(islice(live_audio_stream, n_samples)), 
                 samplerate=sample_rate)

record_and_save_audio_from_microphone('myexample.wav')

# now read that file and display the sound
wf, sr = sf.read('myexample.wav')
disp_wf(wf, sr)
```

![image](https://user-images.githubusercontent.com/1906276/101563806-d1981680-397e-11eb-9f1e-fc35b9b1cc4a.png)
