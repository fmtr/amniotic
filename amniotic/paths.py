from functools import cached_property

from fmtr.tools import PackagePaths


class PackagePaths(PackagePaths):
    """

    Paths

    """

    @cached_property
    def example_700KB(self):
        return self.data / 'audio' / 'file_example_MP3_700KB.mp3'


paths = PackagePaths(org_singleton='fmtr')
