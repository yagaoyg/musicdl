'''
Function:
    Implementation of AlgerMusicClient: http://music.alger.fun/#/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
import time
import json
from contextlib import suppress
from rich.progress import Progress
from urllib.parse import urlencode
from ..sources import BaseMusicClient
from ..utils import resp2json, legalizestring, usesearchheaderscookies, safeextractfromdict, SongInfo, AudioLinkTester, SongInfoUtils


'''AlgerMusicClient'''
class AlgerMusicClient(BaseMusicClient):
    source = 'AlgerMusicClient'
    def __init__(self, **kwargs):
        super(AlgerMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "accept": "application/json, text/plain, */*", "accept-encoding": "gzip, deflate", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "host": "mc.alger.fun", "origin": "http://music.alger.fun", 
            "referer": "http://music.alger.fun/", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'keywords': keyword, 'type': '1', 'limit': 30, 'offset': 0, 'timestamp': str(int(time.time() * 1000)), 'device': 'mobile'}).update(rule)
        # construct search urls
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'http://mc.alger.fun/api/cloudsearch?'
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['limit'] = page_size
            page_rule['offset'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp=resp)['result']['songs']:
                # --download results
                if not isinstance(search_result, dict) or not (song_id := search_result.get('id')): continue
                with suppress(Exception): resp = None; (resp := self.get(f'http://mc.alger.fun/music_proxy/music?id={song_id}', **request_overrides)).raise_for_status()
                download_url_320k = safeextractfromdict((download_result_320k := resp2json(resp=resp)), ['data', 'url'], None)
                download_url_status: dict = self.audio_link_tester.test(url=download_url_320k, request_overrides=request_overrides, renew_session=True)
                with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
                song_info_320k = SongInfo(
                    raw_data={'search': search_result, 'download': download_result_320k, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get("name")), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
                    ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status,
                )
                with suppress(Exception): resp = None; (resp := self.get(f'http://mc.alger.fun/api/song/url/v1?id={song_id}&level=jymaster&encodeType=flac&timestamp={int(time.time() * 1000)}&device=mobile', **request_overrides)).raise_for_status()
                download_url_flac = safeextractfromdict((download_result_flac := resp2json(resp=resp)), ['data', 0, 'url'], None)
                download_url_status: dict = self.audio_link_tester.test(url=download_url_flac, request_overrides=request_overrides, renew_session=True)
                song_info_flac = SongInfo(
                    raw_data={'search': search_result, 'download': download_result_flac, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get("name")), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
                    ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status,
                )
                if song_info_320k.with_valid_download_url and song_info_flac.with_valid_download_url: song_info = song_info_320k if song_info_320k.largerthan(song_info_flac) else song_info_flac
                else: song_info = song_info_320k if song_info_320k.with_valid_download_url else song_info_flac
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                # --lyric results
                with suppress(Exception): (resp := self.get(f"http://mc.alger.fun/api/lyric/new?id={song_id}&timestamp={int(time.time() * 1000)}&device=mobile", **request_overrides)).raise_for_status()
                lyric = safeextractfromdict((lyric_result := resp2json(resp)), ['lrc', 'lyric'], '') or ''
                lyric = "\n".join((lambda o: f"[{o['t']//60000:02d}:{o['t']%60000/1000:05.2f}]{''.join(x.get('tx','') for x in o['c'] if isinstance(x, dict))}")(json.loads(line)) if line.startswith("{") else line for line in lyric.splitlines() if line.strip())
                song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
                song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
            # --update progress
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Error: {err})")
            self.logger_handle.error(f"{self.source}._search >>> {search_url} (Error: {err})", disable_print=self.disable_print)
        # return
        return song_infos