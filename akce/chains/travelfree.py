"""Travel Free (border shops, travel-free.cz): 12-page monthly-ish "akční nabídka" PDF, 4-column grid of tiles.
Title Jost-Bold 9 pt, variety/package Jost-Regular 9 pt, per-litre line Jost-Regular 7 pt ("1 L = Kč 189.66", the "AKCE:"/"CLUB:"
lines carry two of them). Price under the photo in a white rounded box: "Kč " (13 pt regular) + "892" (16 bold) + ".25" (13 bold);
the crossed regular price sits right above in the same box (8/10/8 pt, "Kč" " 1 019" ".75"). Member price: white-on-red
"CLUBCARD Kč 30.35" box under it -> cena = club price, cena_bez = shelf price, podminka "s Travel FREE club kartou".
Prices are "Kč 1 234.56" (prefix, dot decimal, space/narrow-nbsp thousands); the core build_prices reads the split spans
(integer + smaller decimal part) as is, only the narrow no-break space is stripped and the club price is demoted to a
secondary price in is_price (core treats two equal-size prices as two products). Brand banner pages (Valentino, Harry Potter
-20 % "CLUBCARD Kč 611.75") have no product titles and give no offers on purpose."""
import re

from akce.layouts import Layout


class TravelFreeLayout(Layout):
    def is_detail(self, s):
        if not super().is_detail(s):
            return False
        if not getattr(s, "nudged", False):
            s.nudged = True
            s.y0 += 1.5                               # 9 pt lines are set tight under the bold title (box overlaps by ~2.5 pt)
        s.text = re.sub(r"(?<=\d)[ \u202f\u00a0](?=\d{3}\s*(?:g|ml)\b)", "", s.text)             # "1 000 g" -> "1000 g"
        s.text = re.sub(r"(?<![\d,])(\d{1,3})\s*(l|kg|g|ml)\s*=\s*Kč\s*(\d[\d .\u202f\u00a0]*\d)",
                        lambda m: "(=%s %s %s)" % (m.group(1), m.group(2), re.sub(r"[^0-9.]", "", m.group(3))), s.text, flags=re.I)   # "1 L = Kč 2 367.49" -> "(=1 L 2367.49)" (confirms the pair)
        return True

    def is_price(self, s):
        if not super().is_price(s):
            return False
        s.text = re.sub(r"[\u202f\u2002\u00a0 ]", "", s.text)
        if s.text.startswith(".") and not getattr(s, "nudged", False):
            s.nudged = True
            s.x0 += 2.0                               # decimals of the small crossed price overlap the integer by ~1.2 pt
        if s.color == 0xFFFFFF and s.size >= 12:      # white-on-red CLUBCARD price: secondary price of the tile
            s.size = 8.5 if s.text.startswith(".") else 11
        return True


LAYOUT = TravelFreeLayout(
    chain="travelfree",
    title_font=r"Jost-Bold",
    title_size=(8.5, 10.5),
    detail_font=r"Jost-Regular",
    detail_size=(6.5, 9.5),
    price_font=r"Jost-(Bold|Regular)",
    min_price_size=8,
    main_size=15,
    secondary_reach=3.6,
    price_side="below",
    max_dist=300,
    side_penalty=150,
    member_rx=r".",
    member_label="s Travel FREE club kartou",
    skip_words=("novinka", "exclusive", "club", "cena", "sleva", "kč"),
)
