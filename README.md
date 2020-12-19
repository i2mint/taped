
# taped
Python's serene audio accessor


To install:	```pip install taped```


# A quick (audio) peep

## In a nutshell:
    
```python
from taped import LiveWf
live_wf = LiveWf()  # make a live audio waveform object (using defaults for every thing)
live_wf.start()  # start "recording"
wf_chunk = live_wf[:100]  # do stuff (here, grab the first 100 (numerical waveform) samples)
... # do other stuff (save audio, display, pipe into some ML pipeline...)
live_wf.stop()  # stop the live_wf acquisition
```

But obviously, there's more to it. For a quick peep we'll mention just two:
- **context manager**: `LiveWf`, like most stream providing objects, is best used as a context manager (it's that `with...` thing), to automatically "clean up" when finished using.
- **input_device_index**: If you don't specify any arguments when making a `LiveWf`, you'll get defaults. You might want to check them out in case they're not what you want. One crucial argument is the `input_device_index`, which specifies what the audio source actually is. You can get a list of choices by using the `list_recording_device_index_names` function:


```python
from taped import list_recording_device_index_names

list_recording_device_index_names()
```



    [(0, 'MacBook Pro Microphone'), (2, 'ZoomAudioDevice')]




```python
from taped import LiveWf

&#35; you can specify as an integer, a string, or a (int, string) tuple. 
&#35;Bare in mind that both integer index (and sometimes names) may change from one session to another.
input_device_index = 'MacBook Pro Microphone' 

&#35;note how we use a context manager here!
with LiveWf(input_device_index) as live_wf:  # could have also used integer index 0, or both index and name!
    # now live_wf acts (sort of) like a numpy array of live audio waveform
    # skip the first 10000, samples, then and get 110000 samples after that, taking every other sample (i.e. downsampling)
    chk = live_wf[10_000:110_000:2]  
    
len(chk), type(chk)
```



    (22050, list)




```python
from taped import disp_wf
disp_wf(chk, sr=live_wf.sr)  # will sound faster than normal because (remember) we down-sampled.
```


    
![image](https://user-images.githubusercontent.com/1906276/102552725-81a00a80-4076-11eb-9aba-2ecb8b71e36f.png)


    

Note, you can use `find_a_default_input_device_index` to find an input device index for you automatically. 
That's what happens if you don't specify any inputs to `LiveWf()`. 
But don't trust that it will work every time. It's behavior may change, but right now, it just looks for the first name with word `"microphone"` in the list of names, and if that's not found, the first containing `"mic"`.

```python
from taped import find_a_default_input_device_index
input_device_index = find_a_default_input_device_index()
```

## So Basically...

Gives you access to your microphone as an iterator of numerical samples.

```pydocstring
>>> from itertools import islice
>>> from taped import LiveWf
>>>
>>> with LiveWf() as live_wf:
...     first_sample = next(live_wf)  # get a sample
...     second_sample = next(live_wf)  # get the next sample
...     ten_samples = list(islice(live_wf, 7))  # get the next 7 samples, using itertools.islice
...     a_3_6_slice = live_wf[3:6] # skip 3 samples and get 3 more (so up to 6), using [.] instead of islice
...     downsampled = live_wf[0:10:2]  # take every other sample (i.e. down-sampling) using [.]
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
from taped import LiveWf, disp_wf
from itertools import islice

def record_and_display_audio_from_microphone(n_samples=10000, sample_rate=22050):
    with LiveWf(sr=sample_rate) as live_audio_stream:
        wf = list(islice(live_audio_stream, n_samples))
    return disp_wf(wf, sample_rate)

record_and_display_audio_from_microphone()
```

![image](https://user-images.githubusercontent.com/1906276/101562916-289cec00-397d-11eb-8a40-d3a7345e40da.png)


## Record and save audio from microphone

```python
from taped import LiveWf, disp_wf
import soundfile as sf  # pip install soundfile (or get your waveform_to_file function elsewhere)

def record_and_save_audio_from_microphone(filepath='tmp.wav', n_samples=10000, sample_rate=22050):
    with LiveWf(0, sr=sample_rate) as live_audio_stream:
        sf.write(filepath, 
                 data=list(islice(live_audio_stream, n_samples)), 
                 samplerate=sample_rate)

record_and_save_audio_from_microphone('myexample.wav')

# now read that file and display the sound
wf, sr = sf.read('myexample.wav')
disp_wf(wf, sr)
```

![image](https://user-images.githubusercontent.com/1906276/101563806-d1981680-397e-11eb-9f1e-fc35b9b1cc4a.png)


# A few more details

`taped` uses a layered approach. 

The `LiveWf` class you know (and already love) is actually the forth of the following stack of layers:

- `BufferItems`: Provides the items from an audio sensor (also called a mic!); namely the bytes, but also other useful information, such as timestamps (system and sensor).
- `ByteChunks`: Provides chunks of bytes from the mic. Essentially, extracts the bytes that the `BufferItems` items give you.
- `WfChunks`: Provides numerical waveform chunks; by default in the format of `numpy.array` `int16` integers. 
- `LiveWf`: Gives you access to a fixed size buffer of the recent history of audio, in waveform format. Essentially, the `WfChunks` chained together in one continuous (but live/dynamic) array.

Defining a waveform "displayer": if you want to display audio as a spectrogram, and actually play it (in a jupyter notebook), `pip install hum`. 


```python
from contextlib import suppress

try:
    from hum import disp_wf
except ModuleNotFoundError:
    import matplotlib.pylab as plt
    disp_wf = plt.plot
```

Let's get an `input_device_index` to use throughout our demo.


```python
from taped import find_a_default_input_device_index

input_device_index = find_a_default_input_device_index()
```

## BufferItems

`BufferItems` gives you a stream of 5-tuples containing sensor bytes, along with other information (timestamp etc.) 
that `stream2py`, which wraps `PyAudio` (itself a wrapper of `PortAudio`) gives us. 

If you're okay with the high level interfaces that `taped` offers, you may want to skip this `BufferItems` section.
But if you want (or need) to peep under (the first level of) the hood, here's what `BufferItems` is about.


```python
from taped.base import BufferItems

with BufferItems(input_device_index) as buffer_items:
    item = next(buffer_items)

print(f"item is a {type(item).__name__} (a namedtuple) with {len(item)} elements")
for i, x in enumerate(item):
    if isinstance(x, bytes):
        print(f"{i}: {item._fields[i]}: {len(x)} bytes: {x[:4]}...")
    else:
        print(f"{i}: {item._fields[i]}: {x}")
```

    item is a BufferItemOutput (a namedtuple) with 5 elements
    0: timestamp: 1608336556178995
    1: bytes: 8192 bytes: b'\t\x00\x18\x00'...
    2: frame_count: 4096
    3: time_info: {'input_buffer_adc_time': 135079.42883468725, 'current_time': 135079.60533177, 'output_buffer_dac_time': 0.0}
    4: status_flags: 0


```python
from time import sleep
from collections import namedtuple
from pprint import pprint

with BufferItems(input_device_index) as buffer_items:
    it = iter(buffer_items)  # note the iter(buffer_items) instead of just buffer_items!
    item = next(it)
    sleep(2)
    item2 = next(it)
    
data_names = ['timestamp', 'bytes', 'frame_count', 'time_info', 'status_flags']

def display_buffer_item(item):
    d = dict(zip(item._fields, item))
    d['bytes'] = f"{len(d['bytes'])} bytes: {d['bytes'][:4]}..."
    pprint(d)
        
print('\nitem') 
display_buffer_item(item)
print('\nitem2') 
display_buffer_item(item2)
```

    
    item
    {'bytes': "8192 bytes: b'\\x05\\x00\\x0c\\x00'...",
     'frame_count': 4096,
     'status_flags': 0,
     'time_info': {'current_time': 84806.95996904,
                   'input_buffer_adc_time': 84806.78105158823,
                   'output_buffer_dac_time': 0.0},
     'timestamp': 1608236216529112}
    
    item2
    {'bytes': "8192 bytes: b'`\\xffR\\xff'...",
     'frame_count': 4096,
     'status_flags': 0,
     'time_info': {'current_time': 84807.04517719701,
                   'input_buffer_adc_time': 84806.87393594165,
                   'output_buffer_dac_time': 0.0},
     'timestamp': 1608236216621991}

See that the three kind of timestamps that we get are different, 
but all around `4096 / 44100 = 0.09287...`, the chunk size, in seconds.
 
```python
assert buffer_items.chk_size == 4096
assert buffer_items.sr == 44100
print("differences...")
dict(
    timestamp=item2.timestamp - item.timestamp, 
    input_buffer_adc_time = item2.time_info['input_buffer_adc_time'] - item.time_info['input_buffer_adc_time'], 
    current_time = item2.time_info['current_time'] - item.time_info['current_time'],
)

```

    differences...




    {'timestamp': 92879,
     'input_buffer_adc_time': 0.09288435342023149,
     'current_time': 0.0852081570046721}

See that we have different bytes!

```python
assert item.bytes != item2.bytes
```

But add we used `it = buffer_items` directly instead of `it = iter(buffer_items)`, we would have gotten the same bytes.

Indeed, using `iter(...)` ensures that we "move forward" in our iteration, where as doing a `next(buffer_items)` 
would just give us the first chunk of the queue (that is, the oldest one). 
Until the buffer is full, that oldest chunk is always the same first one. 
Once the buffer is full, the `next(buffer_items)` will give us something different (at the rate of incoming chunks).

We can see this by making the buffer size (`stream_buffer_size_s`, whose default is 60 seconds) smaller. 
Study the following code to see what's happening.

```python
import time

def take_a_nap(nap_time):
    print(f"After a {nap_time} seconds nap...")
    time.sleep(nap_time)
    
d = dict()
with BufferItems(stream_buffer_size_s=2) as s:
    d[0] = next(s)
    
    take_a_nap(1)
    d[1] = next(s)
    print(f"... chunk timestamp is {(d[1].timestamp - d[0].timestamp) / 1e6} later\n")
    
    take_a_nap(3)
    d[2] = next(s)
    print(f"... chunk timestamp is {(d[2].timestamp - d[1].timestamp) / 1e6} later\n")

    take_a_nap(1)
    d[3] = next(s)
    print(f"... chunk timestamp is {(d[3].timestamp - d[2].timestamp) / 1e6} later\n")
```

    Found MacBook Pro Microphone. Will use it as the default input device. It's index is 1
    After a 1 seconds nap...
    ... chunk timestamp is 0.0 later
    
    After a 3 seconds nap...
    ... chunk timestamp is 2.229115 later
    
    After a 1 seconds nap...
    ... chunk timestamp is 1.021678 later

## ByteChunks

If you just want the bytes of the sensor, use this.


```python
from taped.base import ByteChunks


with ByteChunks(input_device_index) as byte_chks:
    byte_chk = next(byte_chks)

    
assert isinstance(byte_chk, bytes)  # now we're just getting bytes
len(byte_chk)
```




    8192



## WfChunks

If you want to consume your waveform chunks numpy arrays instead of bytes, use this.


```python
from taped.base import WfChunks


with WfChunks(input_device_index) as wf_chks:
    chk = next(wf_chks)

    
assert isinstance(chk, np.ndarray)  # it's a numpy array
assert isinstance(chk[0], np.int16) # ... of int16 integers
len(chk)
```




    4096



## LiveWf

And finally, if you'd like to imagine you had a single waveform, as an array (populated continuously with live data from your sensor), use this.


```python
from taped.base import LiveWf
from itertools import islice

with LiveWf(input_device_index) as live_wf:
    sample = next(live_wf)  # get one sample
    chk = list(islice(live_wf, 0, 20000))  # get 20K samples
    
assert isinstance(sample, np.int16)  # a sample is an int16
assert len(chk) == 20000  # chk is an array of 20K samples
```


```python
disp_wf(chk)
```



    
![image](https://user-images.githubusercontent.com/1906276/102552830-aeecb880-4076-11eb-8b3e-f02d2b4d42b5.png)

    


You can also access the `list(islice(..., start, stop, step))` samples through the `[...]` brackets interface.


```python
with LiveWf(input_device_index) as live_wf:
    chk = live_wf[10000:54100]  # skip the first 10000, and get 44100 samples after that
    
disp_wf(chk)
```


    
![image](https://user-images.githubusercontent.com/1906276/102552877-c461e280-4076-11eb-86fb-4e5ba338edcb.png)



```python
with LiveWf(input_device_index) as live_wf:
    chk = live_wf[0:44100:2]  # get samples 0 through 44100, but only every other sample (so, downsampling)
    
disp_wf(chk)  # if you listen to it with the sample sample rate, it will sound accelerated!
```


![image](https://user-images.githubusercontent.com/1906276/102552941-e6f3fb80-4076-11eb-81ab-d079a1f74a4b.png)


