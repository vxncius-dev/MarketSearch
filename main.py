import requests, json, shutil
from datetime import datetime
from typing import List, Dict, Tuple, Set, Optional
import streamlit as st
from bs4 import BeautifulSoup
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import pandas as pd


class Market:

    def __init__(self, name: str, link: str,
                 coordinates: List[Tuple[float, float]], hours: Dict[str,
                                                                     str]):
        self.name = name
        self.link = link
        self.coordinates = coordinates
        self.hours = hours

    def is_open(self) -> bool:
        now = datetime.now()
        day_name = now.strftime("%A").lower()
        current_time = now.strftime("%H:%M")
        days_mapping = {
            "monday": "segunda-feira",
            "tuesday": "terça-feira",
            "wednesday": "quarta-feira",
            "thursday": "quinta-feira",
            "friday": "sexta-feira",
            "saturday": "sábado",
            "sunday": "domingo"
        }

        mapped_day_name = days_mapping.get(day_name)
        if mapped_day_name and mapped_day_name in self.hours:
            opening_hours = self.hours[mapped_day_name].split("–")
            return opening_hours[0] <= current_time <= opening_hours[1]

        return False

    def __repr__(self):
        return f"Market(name={self.name}, link={self.link}, coordinates={self.coordinates}, hours={self.hours})"


class PositionRef:

    def __init__(self, current_position: Tuple[float, float],
                 markets: Dict[str, Market]):
        self.current_position = current_position
        self.markets = markets

    def __repr__(self):
        return f"PositionRef(current_position={self.current_position}, markets={self.markets})"


class MarketSearch(PositionRef):

    def __init__(self,
                 current_position: Tuple[float, float],
                 useGuiMode: bool = False):
        self.markets_links = {
            "supermercadogaviao":
            Market(
                "Supermercado Gaviao",
                "https://www.sitemercado.com.br/supermercadogaviao/boa-vista-loja-alvorada-alvorada-av-dos-garimpeiros/busca/",
                [(2.8143964, -60.7579709), (2.8180705, -60.7409135),
                 (2.8180705, -60.7409135)], {
                     "terça-feira": "06:00–23:00",
                     "quarta-feira": "06:00–23:00",
                     "quinta-feira": "06:00–23:00",
                     "sexta-feira": "06:00–23:00",
                     "sábado": "06:00–23:00",
                     "domingo": "06:00–23:00",
                     "segunda-feira": "06:00–23:00"
                 }),
            "supergoiana":
            Market(
                "Supergoiana", "https://supergoiana.com.br/centro/busca/?q=",
                [(2.8143957, -60.7965961), (2.8143957, -60.7965961),
                 (2.818072, -60.7409134), (2.818072, -60.7409134)], {
                     "terça-feira": "07:00–23:00",
                     "quarta-feira": "07:00–23:00",
                     "quinta-feira": "07:00–23:00",
                     "sexta-feira": "07:00–23:00",
                     "sábado": "07:00–23:00",
                     "domingo": "07:00–23:00",
                     "segunda-feira": "07:00–23:00"
                 }),
            "supergoiana_gourmet":
            Market(
                "Supergoiana Gourmet",
                "https://www.supergoiana.com.br/gourmet/busca?q=",
                [(2.8534288, -60.6607366)], {
                    "terça-feira": "06:00–23:00",
                    "quarta-feira": "06:00–23:00",
                    "quinta-feira": "06:00–23:00",
                    "sexta-feira": "06:00–23:00",
                    "sábado": "06:00–23:00",
                    "domingo": "06:00–23:00",
                    "segunda-feira": "06:00–23:00"
                })
        }
        super().__init__(current_position, self.markets_links)
        self.useGuiMode = useGuiMode
        self.outputMethod = st.write if useGuiMode else print
        self.marketProductsSujestionsList: List[str] = [
            "Arroz", "Feijão", "Macarrão", "Lentilha", "Açúcar", "Sal", "Café",
            "Chá", "Óleo de soja", "Vinagre", "Molho de tomate", "Maionese",
            "Mostarda", "Ketchup", "Frutas (maçã, banana, laranja)",
            "Legumes (cenoura, batata, cebola)",
            "Verduras (alface, espinafre, couve)", "Carne bovina", "Frango",
            "Peixe", "Linguiça", "Ovo", "Queijo", "Leite", "Iogurte",
            "Manteiga", "Pão", "Torradas", "Cereais", "Granola", "Biscoitos",
            "Chocolate", "Doces", "Snacks (chips, amendoim)", "Refrigerantes",
            "Sucos", "Água mineral", "Bebidas alcoólicas (cerveja, vinho)",
            "Sabão em pó", "Detergente", "Desinfetante", "Papel toalha",
            "Papel higiênico", "Escova de dentes", "Creme dental", "Shampoo",
            "Condicionador", "Sabonete", "Perfume",
            "Produtos de limpeza (multiuso, limpa vidros)"
        ]

    def printDistanceMarkets(self, showCoordinates: bool = False) -> None:
        distances = []
        for market_key, market in self.markets.items():
            for coordinates in market.coordinates:
                distance = geodesic(self.current_position,
                                    coordinates).kilometers
                if market.is_open():
                    distances.append((market.name, coordinates, distance))

        distances.sort(key=lambda x: x[2])
        console_width = shutil.get_terminal_size().columns
        separator = "=" * (console_width - 2)

        infoMarketOpen: str = "Mercados Abertos por Ordem de Proximidade:"
        if self.useGuiMode:
            st.write(f"**{infoMarketOpen}**")
        else:
            print("\n" + separator)
            print(f"\n{infoMarketOpen}\n")

        if not distances:
            infoNotOpen: str = "Nenhum mercado aberto no momento."
            self.outputMethod(
                f"***{infoNotOpen}***" if self.useGuiMode else infoNotOpen)
            return

        for market_name, coords, distance in distances:
            additional: str = f"em {coords}" if showCoordinates else "da sua posição"
            printSpacement: str = "    " if not self.useGuiMode else ""
            textToshow: str = f"{printSpacement}⚲ {market_name} a {distance:.2f} km {additional}"
            self.outputMethod(textToshow)
        self.outputMethod("")

    def fetch(self, url: str) -> str:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Erro ao buscar URL {url}: {e}")
            return ""

    def formatItems(
            self, uniqueItems: Set[Tuple[str,
                                         str]]) -> List[Tuple[str, float]]:
        items_with_price = []
        for item_name, price in uniqueItems:
            price_value = float(
                price.replace('R$', '').replace(',', '.').strip())
            items_with_price.append((item_name, price_value))

        items_with_price.sort(key=lambda x: x[1])
        return items_with_price

    def printResults(self, items: List[Tuple[str, float]], searchItem: str,
                     market_key: str) -> None:
        if items:
            market_name = self.markets_links[market_key].name
            textResult: str = f"Resultados para {searchItem.capitalize()} em {market_name}:"
            self.outputMethod(
                f"**{textResult}**" if self.useGuiMode else textResult)

            for index, (item_name, price) in enumerate(items):
                price_str: str = f'R$ {price:.2f}'
                itemLabel: str = f'{item_name} - {price_str}'
                printSpacement: str = "    " if not self.useGuiMode else ""
                prefix: str = f'{printSpacement}ⳑ ' if index == len(
                    items) - 1 else f'{printSpacement}⊦ '

                if self.useGuiMode:
                    # if st.button(button_label, key=f"{market_key}_{index}"):
                    #     self.outputMethod(f"Você selecionou: {button_label}")
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        st.write(item_name)

                    with col2:
                        if st.button("Selecionar",
                                     key=f"{market_key}_{index}"):
                            print(f"Você selecionou: {itemLabel}")

                else:
                    self.outputMethod(f'{prefix}{itemLabel}')
                # f{prefix} if not self.useGuiMode else "➤ "

            self.outputMethod("")

        else:
            self.outputMethod("\nProduto não encontrado!")

    def searchPattern(self,
                      market_key: str,
                      searchItem: str,
                      searchItemsLimit=5) -> None:
        if not self.useGuiMode:
            print("\nBuscando item...", end="", flush=True)
        url = f"{self.markets[market_key].link}{searchItem}"
        response_content = self.fetch(url)

        if not response_content:
            return

        soup = BeautifulSoup(response_content, 'html.parser')
        uniqueItems: Set[Tuple[str, str]] = set()

        def getFromJS():
            script_tag = soup.find('script', id='__NEXT_DATA__')
            if script_tag:
                json_data = json.loads(script_tag.string)
                products = json_data.get('props',
                                         {}).get('pageProps',
                                                 {}).get('products', [])

                for product in products:
                    if len(uniqueItems) >= searchItemsLimit:
                        break
                    item_name = product.get('name').title()
                    item_price = f"R$ {product.get('price'):.2f}"
                    uniqueItems.add((item_name, item_price))

        if market_key in ["supergoiana", "supergoiana_gourmet"]:
            getFromJS()
        elif market_key == "supermercadogaviao":
            items = soup.find_all('a',
                                  class_='list-product-link',
                                  attrs={'aria-label': True})
            prices = soup.find_all('div',
                                   class_='area-bloco-preco bloco-preco pr-0')

            for item, price in zip(items, prices):
                if len(uniqueItems) >= searchItemsLimit:
                    break
                item_name = item.get('aria-label').title()
                if item_name:
                    for span in price.find_all('span'):
                        span.extract()
                    price_final = price.get_text(strip=True)
                    uniqueItems.add((item_name, price_final))

        if not self.useGuiMode:
            print("\r" + " " * 20 + "\r", end="", flush=True)

        treatedItems = self.formatItems(uniqueItems)
        self.printResults(treatedItems, searchItem, market_key)

    def show_map(self) -> folium.Map:
        m = folium.Map(location=self.current_position, zoom_start=15)
        folium.Marker(location=self.current_position, popup="Sua Posição Atual", icon=folium.Icon(color='blue')).add_to(m)
        for market in self.markets_links.values():
            for coord in market.coordinates:
                folium.Marker(location=coord, popup=market.name, icon=folium.Icon(color='green')).add_to(m)
        return m

def main(useGUI: Optional[bool]= False) -> None:
    current_position = (2.1072714, -60.6181908)
    market_search = MarketSearch(current_position, useGuiMode=useGUI)
    if useGUI:
        searchItem = st.text_input("", placeholder="Pesquisar produto")
        totalListItems = st.slider("Quantidade de itens para mostrar:", 1, 20,
                                   5)
    else:
        searchItem = input("Pesquisar produto: ")
        totalListItems = input("Quantidade de itens para mostrar: ")
        totalListItems = int(totalListItems) if totalListItems.isdigit() else 5

    if not totalListItems or totalListItems < 1:
        totalListItems = 5

    if searchItem and totalListItems:
        for market_key in market_search.markets.keys():
            market_search.searchPattern(market_key, searchItem, totalListItems)
        market_search.printDistanceMarkets()

    return market_search

if __name__ == "__main__":
    guiMode: bool = True
    market_search = main(useGUI=guiMode)

    if guiMode:
        @st.dialog("Selecione sua posição")
        def showMap(pos):
            st.write(f"Sua Posição Atual: {pos}")
            
            df = pd.DataFrame({
                'col1': [pos[0]],  # Latitude
                'col2': [pos[1]],  # Longitude
                'col3': [100],  # Tamanho, ajuste conforme necessário
                'col4': [[1, 0, 0, 1]]  # Cor, ajuste conforme necessário (RGBA)
            })
            
            st.map(df, latitude="col1", longitude="col2", size="col3", color="col4")
        
        col1, col2 = st.columns([4, 1])

        with col1:
            st.title("Pesquisa de Mercados")

        with col2:
            if st.button("Mostrar Mapa"):
                showMap(market_search.current_position)
                   
        
        hide_streamlit_style = """
        <style>
        #MainMenu {display: none;}
        footer {display: none;}
        </style>
        """
        st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# streamlit run main.py
