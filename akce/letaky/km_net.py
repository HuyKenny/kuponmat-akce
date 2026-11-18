"""Sdílená HTTP session s opakováním pro kuponmat skripty.

PROČ: z Maliny selže zhruba **1 TLS handshake ze 40** při navazování NOVÉHO
spojení; přes sdílenou `requests.Session()` 0 ze 40 (změřeno 21. 9. 2026 na
40 pokusech). Skript, který dělá N nových spojení v cyklu, tím pádem spadne
s pravděpodobností 1-(39/40)^N — u 82 stránek je to ~87 %. Přesně tak dvakrát
spadl `km-overeni-obsahu.py`.

Netýká se to jen cizích webů — 28. 9. 2026 na to spadl i dotaz do vlastního
REST API kuponmatu, takže to není vada protistrany.

Tři skripty (`km-overeni-obsahu.py`, `km-kontrola-cilu.py`, `km-indexace.py`)
dostaly 21. 9. vlastní kopii téhle smyčky. Tenhle modul existuje proto, aby
se nepsala posedmé.

Použití:

    from km_net import SESSION, zkus

    r = zkus(lambda: SESSION.post(url, json=payload, timeout=90))
    if r is None:
        ...  # spojení se nepodařilo navázat ani na N pokusů

`zkus()` **vrací None** místo výjimky, aby volající mohl odlišit „nešlo se
spojit" od „server odpověděl chybou" — to je rozdíl mezi výpadkem sítě
a skutečnou vadou a hlásit se musí různě.
"""
import time

import requests

# Jedna session na celý proces: drží TCP+TLS spojení otevřené, takže další
# dotazy už nový handshake nedělají.
SESSION = requests.Session()

POKUSU = 4
PAUZA = 3.0


def zkus(volani, pokusu=POKUSU, pauza=PAUZA):
    """Zavolá `volani()` a při chybě spojení to zopakuje.

    Opakuje se JEN na `requests.RequestException` (výpadek spojení, timeout).
    HTTP odpověď se vrací tak, jak přišla — i chybová; posoudit ji je na
    volajícím, protože HTTP 403 nebo 429 se opakováním nespraví.

    Vrací odpověď, nebo None, když se spojení nepodařilo navázat.
    """
    for pokus in range(pokusu):
        try:
            return volani()
        except requests.RequestException:
            if pokus == pokusu - 1:
                return None
            time.sleep(pauza)
    return None
