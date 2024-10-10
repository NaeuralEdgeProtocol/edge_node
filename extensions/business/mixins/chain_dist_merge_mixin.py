import os
from naeural_core.local_libraries.vision.ffmpeg_utils import FFMPEGUtils


class _ChainDistMergeMixin(object):
  def __init__(self):
    super(_ChainDistMergeMixin, self).__init__()
    return

  def _merge_concatenate_video_shards(self, video_shards, output_path, upload=True):
    """
    Merge the video shards into a single video file. This method assumes all video shards
    are stored locally.

    Parameters
    ----------
    video_shards : list
        List of video shards to merge.
    output_path : str
        The path to the output file.
    upload : bool, optional
        Upload the output file to minio, by default True

    Returns
    -------
    merged_video : str
        The path to the merged video file. If `upload` is True, then this is the url to the uploaded file.

    """
    ffmpeg_utils = FFMPEGUtils(caller=self)

    os.makedirs(output_path, exist_ok=True)

    merged_video = self.os_path.join(output_path, f"{self.get_stream_id()}_blurred.mp4")
    ffmpeg_utils.concatenate_multiple_video_files(
      input_paths=video_shards,
      output_path=merged_video,
    )

    if not upload:
      return merged_video

    uploaded_video, _ = self.upload_file(
      file_path=merged_video,
      target_path=os.path.join("ChainDist", self.get_stream_id(), f"{os.path.basename(merged_video)}_blurred.mp4"),
    )

    return uploaded_video
