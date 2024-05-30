import os

from core.local_libraries.vision.ffmpeg_utils import FFMPEGUtils


class _ChainDistSplitMixin(object):
  def __init__(self):
    super(_ChainDistSplitMixin, self).__init__()
    return

  def _split_video_file(self, video_file, no_shards, upload=True):
    """
    Split a video file into multiple shards of equal size.

    Parameters
    ----------
    video_file : str
        The path to the video file.
    no_shards : int
        The number of shards to split the video file into.
    upload : bool, optional
        Upload the files to minio, by default True

    Returns
    -------
    dct_ret : dict
        A dictionary containing the following keys:
        - segment_time: the time of each segment
        - output_files: the list of output files
        - errors: the list of errors, if any occurred
    """

    ffmpeg_utils = FFMPEGUtils(caller=self)

    file_path, file_name = self.os_path.split(video_file)
    file_name, _ = self.os_path.splitext(file_name)
    output_path = self.os_path.join(file_path, f"{file_name}_shards")
    os.makedirs(output_path, exist_ok=True)

    dct_ret = ffmpeg_utils.split_video_file(
      path=video_file,
      nr_chunks=no_shards,
      path_to_output=output_path,
    )

    dct_ret["video_resolution"] = ffmpeg_utils.video_resolution(video_file)

    dct_ret["video_frames"] = [
      ffmpeg_utils.no_frames(os.path.join(output_path, file_path))
      for file_path in dct_ret["output_files"]]

    if not upload:
      return dct_ret

    # upload the output files
    output_files = dct_ret["output_files"]
    uploaded_files = []

    for file_path in output_files:
      target_path = os.path.join("ChainDist", self.get_stream_id(), os.path.basename(file_path))
      url, _ = self.upload_file(
        file_path=os.path.join(output_path, file_path),
        target_path=target_path,
      )

      uploaded_files.append(url)

    dct_ret["output_files"] = uploaded_files

    return dct_ret
