// 🔴 2026-07-27 정리 — 스튜디오 좌측 목록을 **지금 올리는 것만** 남겼다.
//
//    뺀 것: 마라탕 1·2·3·5편 · 배달 1편(옵션꼼수) · 피자 1편 · 옛 채널 프로필 ·
//           사장픽 브랜딩(ProfilePick·BannerPick — 올마픽으로 바뀌어 안 씀)
//    지운 게 아니라 **등록만 뺐다.** 파일은 src/shorts/ · src/cards/ 에 그대로 있으니
//    다시 올릴 일이 생기면 import 두 줄만 되살리면 된다.
//
// 🔴 **이름에 한글을 못 쓴다.** remotion 의 validate-composition-id 정규식이
//    `[a-zA-Z0-9-]` 와 한자만 받는다. 한글·언더바를 넣으면 스튜디오가 통째로 에러난다.
//    그래서 **편 번호를 앞에 붙여** 목록에서 순서대로 보이게 했다:
//    폴더 = 한 편, 폴더 안은 늘 같은 3종뿐이다:
//      Video  영상 한 편  /  Thumb  썸네일  /  Card1~4  중간 판
import { Composition, Folder, Still } from "remotion";
import { CabbageBall } from "./olma/CabbageBall";

// ── 원가편 ──
import { TalkBingsu, BINGSU_SEC } from "./shorts/TalkBingsu";
import { ThumbBingsu } from "./cards/ThumbBingsu";
import { BingsuPage } from "./cards/BingsuPage";
import { PAGES as BINGSU_PAGES } from "./cards/pages_bingsu";
import { TalkYeopgi, YEOPGI_SEC } from "./shorts/TalkYeopgi";
import { ThumbYeopgi } from "./cards/ThumbYeopgi";
import { YeopgiPage } from "./cards/YeopgiPage";
import { PAGES as YEOPGI_PAGES } from "./cards/pages_yeopgi";
import { TalkBburinkle, BBURINKLE_SEC } from "./shorts/TalkBburinkle";
import { ThumbBburinkle } from "./cards/ThumbBburinkle";
import { BburinklePage } from "./cards/BburinklePage";
import { PAGES as BB_PAGES } from "./cards/pages_bburinkle";
import { TalkJeyuk, JEYUK_SEC } from "./shorts/TalkJeyuk";
import { ThumbJeyukCost } from "./cards/ThumbJeyukCost";
import { JeyukPage } from "./cards/JeyukPage";
import { PAGES as J_PAGES } from "./cards/pages_jeyuk";
import { TalkSamgye, SAMGYE_SEC } from "./shorts/TalkSamgye";
import { TalkPuradak, PURADAK_SEC } from "./shorts/TalkPuradak";
import { TalkNaengmyeon, NAENGMYEON_SEC } from "./shorts/TalkNaengmyeon";
import { ThumbNaengmyeonCost } from "./cards/ThumbNaengmyeonCost";
import { NaengmyeonPage } from "./cards/NaengmyeonPage";
import { PAGES as N_PAGES } from "./cards/pages_naengmyeon";
import { ThumbPuradakCost } from "./cards/ThumbPuradakCost";
import { PuradakPage } from "./cards/PuradakPage";
import { PAGES as P_PAGES } from "./cards/pages_puradak";
import { ThumbSamgyeCost } from "./cards/ThumbSamgyeCost";
import { SamgyePage } from "./cards/SamgyePage";
import { PAGES as S_PAGES } from "./cards/pages_samgye";
import { TalkZicoba, ZICOBA_SEC } from "./shorts/TalkZicoba";
import { ThumbZicobaCost } from "./cards/ThumbZicobaCost";
import { ZicobaPage } from "./cards/ZicobaPage";
import { PAGES as Z_PAGES } from "./cards/pages_zicoba";
import { TalkGimbap, GIMBAP_SEC } from "./shorts/TalkGimbap";
import { ThumbGimbapCost } from "./cards/ThumbGimbapCost";
import { GimbapPage } from "./cards/GimbapPage";
import { PAGES as G_PAGES } from "./cards/pages_gimbap";
import { TalkDeri, DERI_SEC } from "./shorts/TalkDeri";
import { ThumbDeriCost } from "./cards/ThumbDeriCost";
import { DeriPage } from "./cards/DeriPage";
import { PAGES as D_PAGES } from "./cards/pages_deri";
import { TalkKeunmam, KEUNMAM_SEC } from "./shorts/TalkKeunmam";
import { ThumbKeunmamCost } from "./cards/ThumbKeunmamCost";
import { KeunmamPage } from "./cards/KeunmamPage";
import { PAGES as K_PAGES } from "./cards/pages_keunmam";

// ── 레시피편 (원가편과 짝) ──
import { ShopBburinkle, SHOP_BBU_SEC } from "./shop/ShopBburinkle";
import { ShopZicoba, SHOP_ZICOBA_SEC } from "./shop/ShopZicoba";
import { ThumbRecipe } from "./shop/ThumbRecipe";
import { ThumbZicoba } from "./shop/ThumbZicoba";

// ── 채널 브랜딩 (올마나마) ──
import { ProfileSoft, BannerSoft } from "./cards/Brand";

import { FPS } from "./shorts/config";

const V = { fps: FPS, width: 1080, height: 1920 }; // 쇼츠 규격 — 전 편 공통

export const RemotionRoot = () => {
  return (
    <>
      {/* 🥬 배추 캐릭터 — 검수용 임시 등록 (2026-08-04). 확정되면 편에 붙이고 이 블록은 정리 */}
      <Folder name="X-CabbageTest">
        <Still id="X-Cabbage" component={() => (
          <div style={{ width: 1080, height: 1500, background: "#FBEFE0", display: "flex", alignItems: "flex-start", justifyContent: "center" }}>
            <CabbageBall scale={0.75} />
          </div>
        )} width={1080} height={1500} />
      </Folder>

      {/* 🍔 롯데리아 데리버거 — 이거 얼마남아 8 (2026-08-02)
          🔴 축은 «제일 싼데 제일 안 남는다». 브랜드명을 **쓴다**(검색량 18,870).
             사장님 목소리는 Andrew. 절정 12/16, 홍보는 정점 바로 앞. */}
      <Folder name="8-Deri">
        <Composition id="8-Video" component={TalkDeri}
          durationInFrames={Math.round(DERI_SEC * FPS)} {...V} />
        <Still id="8-Thumb" component={ThumbDeriCost} width={1080} height={1920} />
        {D_PAGES.map((p, i) => (
          <Still key={`d-${i}`} id={`8-Card${i + 1}`} component={DeriPage}
            width={1080} height={1920} defaultProps={{ i }} />
        ))}
      </Folder>

      {/* 🍙 돈까스 김밥 — 이거 얼마남아 7 (브랜드명 안 씀) (2026-08-01)
          🔴 축은 «1등이 돈까스가 아니라 계란». 절정을 12/16(75%)로 미루고
             사이트 홍보를 정점 바로 앞(10~11번)에 끼웠다. 사장님 목소리는 Remy. */}
      <Folder name="7-Gimbap">
        <Composition id="7-Video" component={TalkGimbap}
          durationInFrames={Math.round(GIMBAP_SEC * FPS)} {...V} />
        <Still id="7-Thumb" component={ThumbGimbapCost} width={1080} height={1920} />
        {G_PAGES.map((p, i) => (
          <Still key={`g-${i}`} id={`7-Card${i + 1}`} component={GimbapPage}
            width={1080} height={1920} defaultProps={{ i }} />
        ))}
      </Folder>

      {/* 🥬 깻잎제육 반상 — 이거 얼마남아 9 (2026-08-03)
          🔴 축은 «반찬 네 가지가 다 합쳐 273원». 계란후라이 하나가 그보다 비싸다.
             판매가 10,500원은 공식 API(BF104) 확인값 — DB의 8,900원은 단종된 옛 메뉴다. */}
      <Folder name="9-Jeyuk">
        <Composition id="9-Video" component={TalkJeyuk}
          durationInFrames={Math.round(JEYUK_SEC * FPS)} {...V} />
        <Still id="9-Thumb" component={ThumbJeyukCost} width={1080} height={1920} />
        {J_PAGES.map((p, i) => (
          <Still key={`j-${i}`} id={`9-Card${i + 1}`} component={JeyukPage}
            width={1080} height={1920} defaultProps={{ i }} />
        ))}
      </Folder>

      {/* 🐔 삼계탕 — 이거 얼마남아 11 (2026-08-03)
          🔴 축은 «닭+한방 티백 둘이 92%». 판매가는 한국소비자원 참가격 근거(브랜드 없음). */}
      <Folder name="10-Samgye">
        <Composition id="10-Video" component={TalkSamgye}
          durationInFrames={Math.round(SAMGYE_SEC * FPS)} {...V} />
        <Still id="10-Thumb" component={ThumbSamgyeCost} width={1080} height={1920} />
        {S_PAGES.map((p, i) => (
          <Still key={`s-${i}`} id={`10-Card${i + 1}`} component={SamgyePage}
            width={1080} height={1920} defaultProps={{ i }} />
        ))}
      </Folder>

      {/* 🧄 블랙알리오 치킨 — 이거 얼마남아 10 (2026-08-03)
          🔴 축은 «소스 1,350원이 나머지 셋(1,174원)보다 비싸다». 판매가 21,900원(푸라닭치킨).
             생닭 단가 갱신(4,800→6,000) · 요리페이지 소스를 menus 전용 재료로 통일. */}
      <Folder name="11-Puradak">
        <Composition id="11-Video" component={TalkPuradak}
          durationInFrames={Math.round(PURADAK_SEC * FPS)} {...V} />
        <Still id="11-Thumb" component={ThumbPuradakCost} width={1080} height={1920} />
        {P_PAGES.map((p, i) => (
          <Still key={`p-${i}`} id={`11-Card${i + 1}`} component={PuradakPage}
            width={1080} height={1920} defaultProps={{ i }} />
        ))}
      </Folder>

      {/* 🍜 물냉면 — 이거 얼마남아 13 (2026-08-03)
          🔴 축은 «원가율 12% — 시리즈 최저». 소고기·메밀면·계란 376/330/282원으로
             거의 비슷비슷하다. 판매가 9,000원 — 대표 확정(브랜드 없음, 참가격보다 낮게 잡음). */}
      <Folder name="13-Naengmyeon">
        <Composition id="13-Video" component={TalkNaengmyeon}
          durationInFrames={Math.round(NAENGMYEON_SEC * FPS)} {...V} />
        <Still id="13-Thumb" component={ThumbNaengmyeonCost} width={1080} height={1920} />
        {N_PAGES.map((p, i) => (
          <Still key={`n-${i}`} id={`13-Card${i + 1}`} component={NaengmyeonPage}
            width={1080} height={1920} defaultProps={{ i }} />
        ))}
      </Folder>

      {/* 🔥 지코바 순살양념 — 이거 얼마남아 5 (2026-07-28). 다음 R-Zicoba 레시피편과 짝 */}
      <Folder name="5-Zicoba">
        <Composition id="5-Video" component={TalkZicoba}
          durationInFrames={Math.round(ZICOBA_SEC * FPS)} {...V} />
        <Still id="5-Thumb" component={ThumbZicobaCost} width={1080} height={1920} />
        {Z_PAGES.map((p, i) => (
          <Still key={`z-${i}`} id={`5-Card${i + 1}`} component={ZicobaPage}
            width={1080} height={1920} defaultProps={{ i }} />
        ))}
      </Folder>

      {/* 🍲 순대국 한 그릇 — 이거 얼마남아 6 (2026-07-30)
          🔴 브랜드 이름을 쓰지 않는다 — 일반 순대국 기준(공개 레시피 + 식봄 도매) */}
      <Folder name="6-Keunmam">
        <Composition id="6-Video" component={TalkKeunmam}
          durationInFrames={Math.round(KEUNMAM_SEC * FPS)} {...V} />
        <Still id="6-Thumb" component={ThumbKeunmamCost} width={1080} height={1920} />
        {K_PAGES.map((p, i) => (
          <Still key={`k-${i}`} id={`6-Card${i + 1}`} component={KeunmamPage}
            width={1080} height={1920} defaultProps={{ i }} />
        ))}
      </Folder>

      {/* 🍗 뿌링클 — 이거 얼마남아 4 (2026-07-27). 다음날 R1 레시피편과 짝 */}
      <Folder name="4-Bburinkle">
        <Composition id="4-Video" component={TalkBburinkle}
          durationInFrames={Math.round(BBURINKLE_SEC * FPS)} {...V} />
        <Still id="4-Thumb" component={ThumbBburinkle} width={1080} height={1920} />
        {BB_PAGES.map((p, i) => (
          <Still key={`bb-${i}`} id={`4-Card${i + 1}`} component={BburinklePage}
            width={1080} height={1920} defaultProps={{ i }} />
        ))}
      </Folder>

      {/* 🌶 엽기로제 — 이거 얼마남아 3 (2026-07-26, 업로드 완료) */}
      <Folder name="3-Yeopgi">
        <Composition id="3-Video" component={TalkYeopgi}
          durationInFrames={Math.round(YEOPGI_SEC * FPS)} {...V} />
        <Still id="3-Thumb" component={ThumbYeopgi} width={1080} height={1920} />
        {YEOPGI_PAGES.map((p, i) => (
          <Still key={`yg-${i}`} id={`3-Card${i + 1}`} component={YeopgiPage}
            width={1080} height={1920} defaultProps={{ i }} />
        ))}
      </Folder>

      {/* 🍧 애플망고치즈설빙 — 이거 얼마남아 2 (2026-07-25, 업로드 완료) */}
      <Folder name="2-Bingsu">
        <Composition id="2-Video" component={TalkBingsu}
          durationInFrames={Math.round(BINGSU_SEC * FPS)} {...V} />
        <Still id="2-Thumb" component={ThumbBingsu} width={1080} height={1920} />
        {BINGSU_PAGES.map((p, i) => (
          <Still key={`bs-${i}`} id={`2-Card${i + 1}`} component={BingsuPage}
            width={1080} height={1920} defaultProps={{ i }} />
        ))}
      </Folder>

      {/* 🛒 레시피편 — 원가편 다음날 올리는 짝. 같은 채널로 합쳤다 */}
      <Folder name="R-Recipe">
        <Composition id="R-Bburinkle-Video" component={ShopBburinkle}
          durationInFrames={Math.round(SHOP_BBU_SEC * FPS)} {...V} />
        <Still id="R-Bburinkle-Thumb" component={ThumbRecipe} width={1080} height={1920} />
        <Composition id="R-Zicoba-Video" component={ShopZicoba}
          durationInFrames={Math.round(SHOP_ZICOBA_SEC * FPS)} {...V} />
        <Still id="R-Zicoba-Thumb" component={ThumbZicoba} width={1080} height={1920} />
      </Folder>

      {/* 채널 프로필·배너 — 올마 최신 캐릭터 버전 */}
      <Folder name="Brand">
        <Still id="Brand-Profile" component={ProfileSoft} width={1080} height={1080} />
        <Still id="Brand-Banner" component={BannerSoft} width={2048} height={1152} />
      </Folder>
    </>
  );
};
