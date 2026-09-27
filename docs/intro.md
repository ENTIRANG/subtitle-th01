# 인트로 프리셋

여름방학 영상의 `Prod. NSBD` 인트로. 리졸브에 기본으로 들어 있는 Fusion 타이틀 **Draw On Corners 1 Line** 에 값만 넣은 것이라, 템플릿은 싣지 않고 바꾼 값만 적는다. 기본 템플릿과 원본 컴포지션을 줄 단위로 비교해서 나온 차이가 전부다. 아래 값은 모두 `tokens.json` 의 `intro` 에 있다.

| 노드 | 입력 | 기본값 | 프리셋 | tokens.json |
|---|---|---|---|---|
| Text1 | StyledText | Sample Text | Prod. NSBD | `intro.text` |
| Text1 | Blue1 | 1 | 0.949019607843137 | `intro.text_blue` |
| BoxColor | TopLeftBlue | 1 | 0.949019607843137 | `intro.box_blue` |

글꼴 Open Sans Bold, Size 0.0669, 자간(CharacterSpacing) 1.071 은 기본값 그대로다. 모서리 선 상자의 폭·높이는 템플릿의 표현식이 글자 폭에 맞춘다.

## 클립

| 항목 | 값 | tokens.json |
|---|---|---|
| 길이 | 73프레임 | `intro.length_frames` |
| 영상 페이드 아웃(에디트 페이지 클립 핸들) | 33프레임 | `intro.clip_fade_out_frames` |
| 효과음 | 인트로와 같은 자리에서 시작. 소스 31~122프레임(91프레임), −11.6 dB, 오디오 페이드 아웃 85프레임 | `intro.sfx` |
| 클릭음 | 인트로 시작 + 24프레임. 소스 0~53프레임, −2.8 dB, 오디오 페이드 아웃 4프레임 | `intro.click` |

페이드는 컴포지션이 아니라 편집 페이지 클립에 걸려 있다. 퓨전만 옮기면 끝이 뚝 끊긴다. 효과음 파일은 원본 영상에서 빌려 쓴 것이라 싣지 않는다.

## 스크립트로 넣기

```bash
python scripts/intro_preset.py            # 재생헤드 위치에 "Prod. NSBD"
python scripts/intro_preset.py "Prod. 방송부"
```

현재 타임라인의 재생헤드에 73프레임짜리로 넣고 위 세 값과 영상 페이드 아웃 33프레임을 건다. 값은 실행할 때 `tokens.json` 에서 읽는다. 트랙은 리졸브가 정하는 대상 트랙이다. 29.97·59.94 드롭 프레임 타임코드도 센다. 효과음과 클릭음은 스크립트가 넣지 않는다. 위 표대로 놓는다.

리졸브를 켜 두고 환경설정 → System → General → External scripting using 을 Local 로 둬야 한다. 스크립팅 모듈 위치는 [README 의 스크립트](../README.md#스크립트)에 있다.
