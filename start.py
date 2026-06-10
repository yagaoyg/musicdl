# @misc{musicdl2020,
#     author = {Zhenchao Jin},
#     title = {Musicdl: A lightweight music downloader written in pure python},
#     year = {2020},
#     publisher = {GitHub},
#     journal = {GitHub repository},
#     howpublished = {\url{https://github.com/CharlesPikachu/musicdl}},
# }

from musicdl import musicdl

# 配置项
init_music_clients_cfg = {
    'NeteaseMusicClient': {'work_dir': 'netease'},
    'QQMusicClient': {
        'work_dir': 'qq',
        'preferred_quality': 'high_mp3',  # 跳过无损FLAC, 优先下载高品质MP3 (320kbps)
        'auto_supplement_song': False,    # 不下载LRC歌词文件, 只下载歌曲
    },
}

# 创建客户端
music_client = musicdl.MusicClient(
    music_sources=['NeteaseMusicClient', 'QQMusicClient'],
    init_music_clients_cfg=init_music_clients_cfg,
)

# 下载歌单
song_infos = music_client.parseplaylist("https://y.qq.com/n/ryqq_v2/playlist/7233601871")
music_client.download(song_infos=song_infos)

# 启动交互式界面
# music_client.startcmdui()