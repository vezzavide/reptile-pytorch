from torch.utils import data
import os
import numpy as np
from PIL import Image
from torchvision.datasets.utils import check_integrity, list_dir, list_files

# Might need to manually download, extract, and merge
# https://github.com/brendenlake/omniglot/blob/master/python/images_background.zip
# https://github.com/brendenlake/omniglot/blob/master/python/images_evaluation.zip


def read_image(path, size=None):
    img = Image.open(path, mode='r').convert('L')
    if size is not None:
        img = img.resize(size)
    return img


class ImageCache(object):
    def __init__(self):
        self.cache = {}

    def read_image(self, path, size=None):
        key = (path, size)
        if key not in self.cache:
            self.cache[key] = read_image(path, size)
        else:
            pass  #print 'reusing cache', key
        return self.cache[key]


class FewShot(data.Dataset):
    '''
    Dataset for K-shot N-way classification
    '''
    def __init__(self, paths, meta=None, parent=None):
        self.paths = paths
        self.meta = {} if meta is None else meta
        self.parent = parent

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        path = self.paths[idx]['path']
        if self.parent.cache is None:
            image = read_image(path, self.parent.size)
        else:
            image = self.parent.cache.read_image(path, self.parent.size)
        return image, self.paths[idx]


class AbstractMetaOmniglot(object):

    def __init__(self, characters_list, cache=None, size=(28, 28)):
        self.characters_list = characters_list
        self.cache = cache
        self.size = size

    def __len__(self):
        return len(self.characters_list)

    def __getitem__(self, idx):
        return self.characters_list[idx]

    def get_random_task(self, N=5, K=1):
        all_samples = []
        character_indices = np.random.choice(len(self), N, replace=False)
        for base_idx, idx in enumerate(character_indices):
            character, paths = self.characters_list[idx]
            for path in np.random.choice(paths, K, replace=False):
                new_path = {}
                new_path.update(path)
                new_path['base_idx'] = base_idx
                all_samples.append(new_path)
        base_task = FewShot(all_samples,
                            meta={'characters': character_indices},
                            parent=self
                            )
        return base_task


class MetaOmniglotFolder(AbstractMetaOmniglot):

    def __init__(self, root='omniglot', cache=None, size=(28, 28)):
        '''
        :param root: folder containing alphabets for background and evaluation set
        '''
        self.root = root
        self.alphabets = list_dir(root)
        self._characters = {}
        for alphabet in self.alphabets:
            for character in list_dir(os.path.join(root, alphabet)):
                full_character = os.path.join(root, alphabet, character)
                character_idx = len(self._characters)
                self._characters[full_character] = []
                for filename in list_files(full_character, '.png'):
                    self._characters[full_character].append({
                        'path': os.path.join(root, alphabet, character, filename),
                        'character_idx': character_idx
                    })
        characters_list = np.asarray(self._characters.items())
        AbstractMetaOmniglot.__init__(self, characters_list, cache, size)


class MetaOmniglotSplit(AbstractMetaOmniglot):

    pass


def split_omniglot(meta_omniglot, validation=0.1):
    n_val = int(validation * len(meta_omniglot))
    indices = np.arange(len(meta_omniglot))
    np.random.shuffle(indices)
    train_characters = meta_omniglot[indices[:-n_val]]
    test_characters = meta_omniglot[indices[-n_val:]]
    train = MetaOmniglotSplit(train_characters, cache=meta_omniglot.cache, size=meta_omniglot.size)
    test = MetaOmniglotSplit(test_characters, cache=meta_omniglot.cache, size=meta_omniglot.size)
    return train, test



meta_omniglot = MetaOmniglotFolder('omniglot', size=(64, 64), cache=ImageCache())

train, test = split_omniglot(meta_omniglot)
print 'all', len(meta_omniglot)
print 'train', len(train)
print 'test', len(test)

base_task = train.get_random_task()
print 'base_task', len(base_task)
print 'ask once', base_task[0]
print 'ask twice', base_task[0]

