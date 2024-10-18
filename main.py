import requests
import json
from datetime import datetime
from typing import List, Dict, Tuple, Set
import streamlit as st
from bs4 import BeautifulSoup
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium


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

    def __repr__(self) -> str:
        return (f"Market(name={self.name}, link={self.link}, "
                f"coordinates={self.coordinates}, hours={self.hours})")


class PositionRef:

    def __init__(self, current_position: Tuple[float, float],
                 markets: Dict[str, Market]):
        self.current_position = current_position
        self.markets = markets

    def __repr__(self) -> str:
        return (f"PositionRef(current_position={self.current_position}, "
                f"markets={self.markets})")


class MarketSearch(PositionRef):

    def __init__(self):
        with open('conf.json', 'r') as conf_file:
            conf_data = json.load(conf_file)
        initial_position = tuple(conf_data['coordinates'])

        with open('markets.json', 'r') as markets_file:
            markets_data = json.load(markets_file)
            markets = {
                name: Market(**data)
                for name, data in markets_data.items()
            }

        with open('suggestions.json', 'r') as suggestions_file:
            self.product_suggestions = json.load(suggestions_file)

        super().__init__(initial_position, markets)
        self.main()

    @staticmethod
    def fetch(url: str) -> str:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Erro ao buscar URL {url}: {e}")
            return ""

    def filter_suggestions(self, query: str) -> List[str]:
        if not query:
            return []

        matched_items = [
            item for item in self.product_suggestions.keys()
            if item.lower().startswith(query.lower())
        ]

        related_suggestions = []
        for item in matched_items:
            related_suggestions.extend(self.product_suggestions[item])

        related_suggestions = list(set(related_suggestions))
        return [item for item in related_suggestions if item.lower() != query.lower()]


    def print_distance_markets(self, show_coordinates: bool = False) -> None:
        distances = []
        for market_key, market in self.markets.items():
            for coordinates in market.coordinates:
                distance = geodesic(self.current_position,
                                    coordinates).kilometers
                if market.is_open():
                    distances.append((market.name, coordinates, distance))

        distances.sort(key=lambda x: x[2])
        info_market_open = "Mercados Abertos por Ordem de Proximidade:"
        st.subheader(f"{info_market_open}", divider="gray")

        if not distances:
            st.write("***Nenhum mercado aberto no momento***")
            return

        for market_name, coords, distance in distances:
            additional = f"em {coords}" if show_coordinates else "da sua posição"
            text_to_show = f"⚲ {market_name} a {distance:.2f} km {additional}"
            st.write(text_to_show)
        st.write("")

    def format_items(
            self, unique_items: Set[Tuple[str,
                                          str]]) -> List[Tuple[str, float]]:
        items_with_price = []
        for item_name, price in unique_items:
            price_value = float(
                price.replace('R$', '').replace(',', '.').strip())
            items_with_price.append((item_name, price_value))

        items_with_price.sort(key=lambda x: x[1])
        return items_with_price

    def print_results(self, items: List[Tuple[str, float]], search_item: str,
                      market_key: str) -> None:
        if items:
            market_name = self.markets[market_key].name
            st.subheader(
                f"Resultados para {search_item.capitalize()} em {market_name}:",
                divider="gray")

            for index, (item_name, price) in enumerate(items):
                price_str = f'R$ {price:.2f}'
                item_label = f'{item_name} - {price_str}'

                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(item_name)

                with col2:
                    if st.button("Selecionar", key=f"{market_key}_{index}"):
                        print(f"Você selecionou: {item_label}")

            st.write("")
        else:
            st.write("\nProduto não encontrado!")

    def search_pattern(self,
                       market_key: str,
                       search_item: str,
                       search_items_limit: int = 5) -> None:
        url = f"{self.markets[market_key].link}{search_item}"
        response_content = self.fetch(url)

        if not response_content:
            return

        soup = BeautifulSoup(response_content, 'html.parser')
        unique_items: Set[Tuple[str, str]] = set()

        def get_from_js() -> None:
            script_tag = soup.find('script', id='__NEXT_DATA__')
            if script_tag:
                json_data = json.loads(script_tag.string)
                products = json_data.get('props',
                                         {}).get('pageProps',
                                                 {}).get('products', [])

                for product in products:
                    if len(unique_items) >= search_items_limit:
                        break
                    item_name = product.get('name').title()
                    item_price = f"R$ {product.get('price'):.2f}"
                    unique_items.add((item_name, item_price))

        if market_key in ["supergoiana", "supergoiana_gourmet"]:
            get_from_js()
        elif market_key == "supermercadogaviao":
            items = soup.find_all('a',
                                  class_='list-product-link',
                                  attrs={'aria-label': True})
            prices = soup.find_all('div',
                                   class_='area-bloco-preco bloco-preco pr-0')

            for item, price in zip(items, prices):
                if len(unique_items) >= search_items_limit:
                    break
                item_name = item.get('aria-label').title()
                if item_name:
                    for span in price.find_all('span'):
                        span.extract()
                    price_final = price.get_text(strip=True)
                    unique_items.add((item_name, price_final))

        treated_items = self.format_items(unique_items)
        self.print_results(treated_items, search_item, market_key)

    def show_map(self, pos: Tuple[float, float]) -> folium.Map:
        m = folium.Map(location=pos, zoom_start=15)
        folium.Marker(location=pos,
                      popup="Sua Posição Atual",
                      icon=folium.Icon(color='blue')).add_to(m)

        for market_key, market in self.markets.items():
            for coord in market.coordinates:
                folium.Marker(location=coord,
                              popup=market.name,
                              icon=folium.Icon(color='green')).add_to(m)
        return m

    @st.dialog("Selecione sua posição")
    def show_map_dialog(self, pos: Tuple[float, float]) -> None:
        st.write(f"Sua Posição Atual: {pos}")
        m = folium.Map(location=pos, zoom_start=15)

        folium.Marker(location=pos,
                      popup="Sua Posição Atual",
                      icon=folium.Icon(color='blue')).add_to(m)

        for market_key, market in self.markets.items():
            for coords in market.coordinates:
                folium.Marker(location=coords,
                              popup=market.name,
                              icon=folium.Icon(color='red')).add_to(m)
                folium.PolyLine(locations=[pos, coords],
                                color="#fe4f03",
                                weight=2.5,
                                opacity=1).add_to(m)

        st_folium(m, width=400, height=400)

    def main(self) -> None:
        col1, col2 = st.columns([4, 1], vertical_alignment="bottom")

        with col1:
            st.title("Market Search")

        with col2:
            if st.button("Mostrar Mapa"):
                self.show_map_dialog(self.current_position)

        search_item = st.text_input("", placeholder="Pesquisar produto")
        total_list_items = st.slider("Quantidade de itens para mostrar:", 1,
                                     20, 4)
        if not total_list_items or total_list_items < 1:
            total_list_items = 5

        if search_item:
            suggestions = self.filter_suggestions(search_item)
            if suggestions:
                suggestions_text = ", ".join(suggestions)
                st.write(f"Sugestões: {suggestions_text}")
            else:
                st.write("Nenhuma sugestão encontrada.")

        if not total_list_items or total_list_items < 1:
            total_list_items = 5

        if search_item and total_list_items:
            for market_key in self.markets.keys():
                self.search_pattern(market_key, search_item, total_list_items)
            self.print_distance_markets()

        hide_streamlit_style = """
        <style>
        #MainMenu {display: none;}
        footer {display: none;}
        </style>
        """
        st.markdown(hide_streamlit_style, unsafe_allow_html=True)


if __name__ == "__main__":
    MarketSearch()
