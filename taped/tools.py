from taped.base import BaseBufferItems
from taped.util import DFLT_SR, DFLT_SAMPLE_WIDTH, DFLT_CHK_SIZE, DFLT_STREAM_BUF_SIZE_S


def record_some_sound(
    save_to_file,
    input_device_index=None,
    sr=DFLT_SR,
    sample_width=DFLT_SAMPLE_WIDTH,
    chk_size=DFLT_CHK_SIZE,
    stream_buffer_size_s=DFLT_STREAM_BUF_SIZE_S,
    verbose=True,
):
    def get_write_file_stream():
        if isinstance(save_to_file, str):
            return open(save_to_file, 'wb')
        else:
            return save_to_file  # assume it's already a stream

    def clog(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    buffer_items = BaseBufferItems(
        input_device_index=input_device_index,
        sr=sr,
        sample_width=sample_width,
        chk_size=chk_size,
        stream_buffer_size_s=stream_buffer_size_s,
    )
    with buffer_items:
        """keep open and save to file until stop event"""
        clog('starting the recording (you can KeyboardInterrupt at any point)...')
        with get_write_file_stream() as write_stream:
            for item in buffer_items:
                try:
                    write_stream.write(item.bytes)
                except KeyboardInterrupt:
                    clog('stopping the recording...')
                    break

    clog('Done.')
