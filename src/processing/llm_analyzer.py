from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

device = torch.device("cuda") if torch.cuda.is_available() else "cpu"

model_name = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

premise = """Witam, mam na sprzedaż CLIO
FULL OPCJA !!!
Alpine
Rocznik 2024
16tys.km
GWARANCJA PRZEBIEGU, PRZEBIEG POTWIERDZONY
BARDZO BOGATE WYPOSAŻENIE
nawigacja
Duży tablet
Alufelgi
Martwe pole
Pół skóry
czarna podsufitka
Klimatyzacja automatyczna
Kamera
Asystent pasa ruchu
tempomat aktywny
Wykrywanie przeszkód
Lampy full led
czujniki parkowania
czujnik deszczu i zmierzchu
Kierownica wielofunkcyjna
Elektryczne szyby
Elektryczne lusterka
Podgrzewane lusterka
Zestaw głośnomówiący
Wspomaganie
Centralny zamek
USB
AuX
Itd.
WNĘTRZE BARDZO ZADBANE
BARDZO ŁADNA TAPICERKA
sprowadzony z Francji od 1 właściciela
Uszkodzony jak na załączonych zdjęciach
Airbag OK
Pali i jeździ
ZAPRASZAM DO OSTROWA WIELKOPOLSKIEGO
Tel5096dwa4813
Więcej informacji udzielam telefonicznie
Niniejsze ogłoszenie jest wyłącznie informacją handlową i nie stanowi oferty w myśl art. 66, § 1. Kodeksu Cywilnego. Sprzedający nie odpowiada za ewentualne błędy ogłoszenia.
ZAPIS TEN ZOSTAŁ ZAWARTY ZE WZGLĘDU NA MOŻLIWOŚĆ NIEZAMIERZONYCH POMYŁEK. JEŻELI ZAUWAŻYSZ NIEŚCISŁOŚĆ - NAPISZ DO MNIE"""

hypothesis = "Samochód był sprowadzony z zagranicy (spoza Polski)."

input = tokenizer(premise, hypothesis, truncation = True, return_tensors = "pt")
output = model(input["input_ids"].to(device))
prediction = torch.softmax(output['logits'][0], -1).tolist()
label_names = ["entailment", "neutral", "contradiction"]
prediction = {name: round(float(pred) * 100, 1) for pred, name in zip(prediction, label_names)}
print(prediction)