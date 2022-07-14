# ibus-hiragana - Hiragana IME for IBus
#
# Copyright (c) 2017-2022 Esrille Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import package

import os
import logging
import re

logger = logging.getLogger(__name__)

DICTIONARY_VERSION = "v0.4.0"
NON_YOMIGANA = re.compile(r'[^ぁ-ゖァ-ー―]')
YOMIGANA = re.compile(r'^[ぁ-ゖァ-ー―]+[、。，．]?$')
HIRAGANA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぁぃぅぇぉゃゅょっぱぴぷぺぽゔ"
TYOUON = "あいうえおあいうえおあいうえおあいうえおあいうえおあいうえおあいうえおあうおあいうえおあおんあいうえおあいうえおあいうえおあいうえおあいうえおあうおうあいうえおう"
OKURIGANA = re.compile(r'[ぁ-ゖ1iIkKgsStnbmrwW235]+$')
KATUYOU = {
    '1': ("", "る", "れば", "ろ", "よう", "て", "た", "な", "た", "ま", "ず", None, None),
    'i': ("く", "い", "ければ", None, "かろう", "くて", "かった", None, None, None, None, None, None, ""),
    'I': ("く", "い", "ければ", None, "かろう", "くて", "かった", None, None, None, None, None, None, "", "な"),   # 小さい, 大きい
    'k': ("き", "く", "けば", "け", "こう", "いて", "いた", "かな", "きた", "きま", "かず", "かせ", "かれ"),
    'K': ("き", "く", "けば", "け", "こう", "って", "った", "かな", "きた", "きま", "かず", "かせ", "かれ"),  # 行く
    'g': ("ぎ", "ぐ", "げば", "げ", "ごう", "いで", "いだ", "がな", "ぎた", "ぎま", "がず", "がせ", "がれ"),
    's': ("し", "す", "せば", "せ", "そう", "して", "した", "さな", "した", "しま", "さず", "させ", "され"),
    'S': ("し", "する", "すれば", "しろ", "しよう", "して", "した", "しな", "した", "しま", "せず", "させ", "され"),  # 欲S
    't': ("ち", "つ", "てば", "て", "とう", "って", "った", "たな", "ちた", "ちま", "たず", "たせ", "たれ"),
    'n': ("に", "ぬ", "ねば", "ね", "のう", "んで", "んだ", "なな", "にた", "にま", "なず", "なせ", "なれ"),
    'b': ("び", "ぶ", "べば", "べ", "ぼう", "んで", "んだ", "ばな", "びた", "びま", "ばず", "ばせ", "ばれ"),
    'm': ("み", "む", "めば", "め", "もう", "んで", "んだ", "まな", "みた", "みま", "まず", "ませ", "まれ"),
    'r': ("り", "る", "れば", "れ", "ろう", "って", "った", "らな", "りた", "りま", "らず", "らせ", "られ"),
    'w': ("い", "う", "えば", "え", "おう", "って", "った", "わな", "いた", "いま", "わず", "わせ", "われ"),
    'W': ("い", "う", "えば", "え", "おう", "うて", "うた", "わな", "いた", "いま", "わず", "わせ", "われ"),  # 問う, 請う, 乞う, etc.
    '2': ("", None, None, None, None, "て", "た", None, "た", "ま", None, None, None),  # きて
    '3': (None, "る", "れば", None, None, None, None, None, None, None, None, None, None),  # くる
    '5': (None, None, None, "い", "よう", None, None, "な", None, None, "ず", "させ", "られ"),  # こい
}
DAKUON = "がぎぐげござじずぜぞだぢづでどばびぶべぼ"
SEION = "かきくけこさしすせそたちつてとはひふへほ"


class Dictionary:

    @staticmethod
    def opt_len(x):
        return 0 if x is None else len(x)

    # Compare okuri and yomi ignoring the Dakuten of the last character
    @staticmethod
    def strdcmp(okuri, yomi):
        assert 0 < len(yomi)
        last = len(yomi) - 1
        pos = DAKUON.find(okuri[last])
        if 0 <= pos:
            okuri = okuri[:last] + SEION[pos]
            if okuri == yomi:
                return True
        return False

    def __init__(self, path, user, clear_history=False):
        logger.info(f'Dictionary("{path}", "{user}")')

        self._dict_base = {}
        self._dict = {}

        self._yomi = ''
        self._no = 0
        self._cand = []
        self._order = []
        self._completed = []
        self._numeric = ''
        self._dirty = False

        self._orders_path = ''

        try:
            # Load Katakana dictionary first so that Katakana words come after Kanji words.
            katakana_path = os.path.join(package.get_datadir(), 'katakana.dic')
            self._load_dict(self._dict_base, katakana_path)
            # Load system dictionary
            self._load_dict(self._dict_base, path)
        except Exception as error:
            logger.error(error)

        # Load private dictionary
        self._dict = self._dict_base.copy()
        if user:
            my_path = os.path.join(package.get_user_datadir(), user)
            self._load_dict(self._dict, my_path, 'a+')

        base = os.path.basename(path)
        if base:
            self._orders_path = os.path.join(package.get_user_datadir(), base)
            if clear_history:
                logger.info('clear_history')
                with open(self._orders_path, 'w') as file:
                    file.write("; " + DICTIONARY_VERSION + "\n")
            self._load_dict(self._dict, self._orders_path, 'a+', version_checked=False)

    def _load_dict(self, dict, path, mode='r', version_checked=True):
        reorder_only = not version_checked
        with open(path, mode) as file:
            file.seek(0, 0)   # in case opened in the 'a+' mode
            for line in file:
                line = line.strip(' \n/')
                if not line:
                    continue
                if line[0] == ';':
                    if line == "; " + DICTIONARY_VERSION:
                        version_checked = True
                    continue
                if not version_checked:
                    continue
                p = line.split(' ', 1)
                yomi = p[0]
                cand = p[1].strip(' \n/').split('/')
                self._merge_entry(dict, yomi, cand, reorder_only)
                if yomi.endswith('―'):
                    self._merge_entry(dict, yomi[:-1], [yomi], reorder_only)
                yomi99 = self._to_99(yomi)
                if yomi99 != yomi:
                    self._merge_entry(dict, yomi99, cand, reorder_only)
                    if yomi.endswith('―'):
                        self._merge_entry(dict, yomi99[:-1], [yomi], reorder_only)
            logger.info(f'Loaded {path}')

    def _merge_entry(self, dict, yomi, cand, reorder_only):
        if reorder_only:
            if yomi in dict:
                update = list(dict[yomi])
                for i in reversed(cand):
                    if i in update:
                        update.remove(i)
                        update.insert(0, i)
                dict[yomi] = update
        elif yomi not in dict:
            dict[yomi] = cand
        else:
            update = list(dict[yomi])
            for i in reversed(cand):
                if i in update:
                    update.remove(i)
                update.insert(0, i)
            dict[yomi] = update

    def _to_99(self, s):
        t = ''
        b = ''
        for c in s:
            if c == 'ー' and b:
                i = HIRAGANA.find(b)
                if i == -1:
                    t += c
                else:
                    t += TYOUON[i]
            else:
                t += c
            b = c
        return t

    def reset(self):
        self._yomi = ''

    def not_selected(self):
        return self._no == 0

    def next(self):
        if self._no + 1 < len(self._cand):
            self._no += 1
        return self._cand[self._no]

    def previous(self):
        if 0 < self._no:
            self._no -= 1
        return self._cand[self._no]

    def current(self):
        if self._yomi:
            return self._cand[self._no]
        return ''

    def set_current(self, index):
        index = int(index)
        if self._yomi and 0 <= index and index < len(self._cand):
            self._no = index

    def reading(self):
        return self._yomi

    def cand(self):
        if self._yomi:
            return self._cand
        return []

    # -1: yomi is not valid
    # 0: yomi can be valid; still missing a few letters
    # 1: yomi is valid
    def _match(self, okuri, yomi):
        if okuri and 0 <= "1iIkKgsStnbmrwW235".find(okuri[-1]):
            suffix = okuri[-1]
            okuri = okuri[:-1]
        else:
            suffix = ''
        pos = min(len(okuri), len(yomi))

        # Check the fixed part of Okurigana
        if okuri:
            if yomi[:pos] == okuri[:pos]:
                if pos == len(okuri):
                    if not suffix:
                        return 1 if len(okuri) < len(yomi) else 0
                else:
                    return 0
            elif len(okuri) < len(yomi):
                return -1
            elif self.strdcmp(okuri, yomi):
                return 0
            else:
                return -1

        # Check conjugations
        assert suffix
        assert pos == len(okuri)
        yomi = yomi[pos:]
        if not yomi:
            return 0
        katuyou = KATUYOU.get(suffix, None)
        if katuyou is None:
            return -1
        conj_len = len(max(katuyou, key=self.opt_len))
        for i in range(min(len(yomi), conj_len), 0, -1):
            for k in katuyou:
                if k is None or len(k) <= i:
                    continue
                if len(yomi) < len(k) and (k[:i] == yomi[:i] or self.strdcmp(k[:i], yomi[:i])):
                    return 0
            for k in katuyou:
                if k is None or len(k) != i:
                    continue
                if k == yomi[:i]:
                    return 1 if i < len(yomi) else 0
                elif len(yomi) == len(k) and self.strdcmp(k, yomi[:i]):
                    return 0

        # cf. 食べ
        if "" in katuyou:
            return 1 if 0 < len(yomi) else 0

        return -1

    def lookup(self, yomi, pos):
        logger.debug(f'lookup({yomi}, {pos})')

        self.reset()
        # Look for the nearest hyphen.
        suffix = yomi[:pos].rfind('―')
        if 0 <= suffix and not YOMIGANA.match(yomi[suffix:pos]):
            suffix = -1
        if suffix <= 0:
            numeric = ''
            has_numeric = False
            size = pos
            for i in range(size - 1, -1, -1):
                if not has_numeric and yomi[i].isnumeric():
                    numeric = yomi[i] + numeric
                    if 0 < i and yomi[i - 1].isnumeric():
                        continue
                    has_numeric = True
                elif NON_YOMIGANA.match(yomi[i]):
                    break
                y = yomi[i:size]
                if not has_numeric:
                    if y in self._dict:
                        self._yomi = y
                        self._cand = self._dict[y]
                        self._no = 0
                        self._order = []
                        self._completed = []
                        self._numeric = ''
                else:
                    yy = y.replace(numeric, '#')
                    if yy in self._dict:
                        self._yomi = yy[1:]
                        cand = []
                        for c in self._dict[yy]:
                            cand.append(c[1:])
                        self._cand = cand
                        self._no = 0
                        self._order = []
                        self._completed = []
                        self._numeric = numeric
            return self.current()

        # Process suffix
        size = suffix + 1
        y = yomi
        for i in range(len(yomi[size:])):
            if NON_YOMIGANA.match(yomi[size + i]):
                y = y[:size + i]
                break
        for i in range(size - 2, -1, -1):
            if NON_YOMIGANA.match(y[i]):
                break
            if y[i:size] in self._dict:
                cand = []
                order = []
                completed = []
                n = 0
                for c in self._dict[y[i:size]]:
                    pattern = OKURIGANA.search(c)
                    if pattern:
                        pos_okuri = pattern.start()
                    else:
                        pos_okuri = len(c)
                    okuri = c[pos_okuri:]
                    p = self._match(okuri, y[size:])
                    logger.debug(f'lookup: {c} {y[size:]} => {p}')
                    c = c[:pos_okuri] + yomi[size:pos]
                    if 0 <= p and c not in cand:
                        cand.append(c)
                        order.append(n)
                        completed.append(p)
                    n += 1
                if cand:
                    self._yomi = yomi[i:pos]
                    self._cand = cand
                    self._no = 0
                    self._order = order
                    self._completed = completed
                    self._numeric = ''
        return self.current()

    # Check if the current yougen is completed
    def is_complete(self):
        current = self.current()
        if not current:
            return True
        if '―' in current[-1]:
            return False
        pos_suffix = self._yomi.rfind('―')
        if pos_suffix <= 0:
            return True
        size = pos_suffix + 1
        if size == len(self._yomi):
            return False
        return 0 if 0 in self._completed else 1

    def confirm(self, shrunk):
        if not self._yomi:
            return

        # Get a copy of the original candidate list
        yomi = self._yomi
        no = self._no

        if self._order:
            yomi = yomi[:yomi.find('―') + 1]
            no = self._order[no]
            cand = self._dict[yomi][:]
        elif self._numeric:
            yomi = '#' + yomi
            cand = []
            for c in self._cand:
                cand.append('#' + c)
        else:
            cand = self._cand[:]

        # Update the order of the candidates.
        first = cand[no]
        if 0 < no:
            cand.remove(first)
            cand.insert(0, first)
            self._dict[yomi] = cand
            self._dirty = True

        # Personalize the dictionary if the candidate has been selected by shrinking the reading.
        if shrunk and not self._order and not self._numeric:
            yomi = shrunk + yomi
            if self.lookup(yomi, len(yomi)):
                first = shrunk + first
                cand = self._cand[:]
                try:
                    cand.remove(first)
                except ValueError:
                    pass
                cand.insert(0, first)
                self._dict[yomi] = cand
                self._dirty = True

    def create_pseudo_candidate(self, text):
        self._yomi = text
        self._cand = [text]
        self._completed = [-1]
        self._no = 0
        self._numeric = ''

    def save_orders(self):
        if not self._dirty:
            return
        with open(self._orders_path, 'w') as file:
            file.write("; " + DICTIONARY_VERSION + "\n")
            for yomi, cand in self._dict.items():
                if yomi not in self._dict_base or cand != self._dict_base[yomi]:
                    file.write(yomi + " /" + '/'.join(cand) + "/\n")
        self._dirty = False

    def dump(self):
        print('\'', self._yomi, '\' ', self._no, ' ', self._cand, sep='')
