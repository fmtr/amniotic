from functools import cached_property

from corio import PackagePaths


class PackagePaths(PackagePaths):
    """

    Paths

    """

    @cached_property
    def audio(self):
        return self.data / 'audio'

    @cached_property
    def config(self):
        return self.data / 'config'

    @cached_property
    def themes(self):
        return self.config / 'themes'

    @cached_property
    def example_700KB(self):
        return self.audio / 'file_example_MP3_700KB.mp3'

    @cached_property
    def gambling(self):
        return self.audio / 'A Good Bass for Gambling.mp3'


paths = PackagePaths()
paths
