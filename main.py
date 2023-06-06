import pathlib
import tomllib
from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client
from pyrogram.types import Photo


@dataclass(frozen=True, slots=True)
class Config:
    api_id: int
    api_hash: str
    timezone: ZoneInfo
    font_file_path: pathlib.Path


def load_config(config_file_path: pathlib.Path) -> Config:
    raw_config = config_file_path.read_text(encoding='utf-8')
    config = tomllib.loads(raw_config)
    return Config(
        api_id=config['telegram_account']['api_id'],
        api_hash=config['telegram_account']['api_hash'],
        timezone=ZoneInfo(config['timezone']),
        font_file_path=pathlib.Path(config['assets']['font_file_path']),
    )


async def get_my_photos(client: Client) -> list[Photo]:
    return [photo async for photo in client.get_chat_photos('me')]


async def set_image(client: Client) -> None:
    photos = await get_my_photos(client)
    await client.delete_profile_photos([p.file_id for p in photos[1:]])
    with open('./.avatar.png', 'rb') as file:
        await client.set_profile_photo(photo=file)


class Coordinates(NamedTuple):
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Theme:
    background_color: str
    font_color: str


@dataclass(frozen=True, slots=True)
class ImageGenerator:
    current_time: datetime
    font_file_path: pathlib.Path

    @property
    def current_time_text(self) -> str:
        return f'{self.current_time:%H:%M}'

    def calculate_text_coordinates(
            self,
            draw: ImageDraw,
            font: ImageFont,
            width: int,
            height: int,
    ) -> Coordinates:
        bbox = draw.textbbox((0, 0), self.current_time_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2 - 50
        return Coordinates(x=x, y=y)

    def generate(self, theme: Theme):
        width = height = 500
        image = Image.new(
            mode='RGB',
            size=(width, height),
            color=theme.background_color,
        )
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(
            font=str(self.font_file_path.resolve()),
            size=120
        )
        text_coordinates = self.calculate_text_coordinates(
            draw=draw,
            font=font,
            width=width,
            height=height,
        )
        draw.text(
            xy=text_coordinates,
            text=self.current_time_text,
            fill=theme.font_color,
            font=font,
        )
        image.save('./.avatar.png')


def is_day(now: datetime) -> bool:
    start = now.replace(
        hour=8,
        minute=0,
        microsecond=0
    )
    end = now.replace(
        hour=20,
        minute=0,
        microsecond=0
    )
    return start <= now <= end


def main() -> None:
    config_file_path = pathlib.Path(__file__).parent / 'config.toml'
    config = load_config(config_file_path)

    client = Client(
        '.pyrogram_client',
        api_id=config.api_id,
        api_hash=config.api_hash,
    )
    client.start()

    now = datetime.now(config.timezone)

    dark_theme = Theme(background_color='black', font_color='white')
    light_theme = Theme(background_color='white', font_color='black')

    theme = light_theme if is_day(now) else dark_theme

    image_generator = ImageGenerator(
        current_time=now,
        font_file_path=config.font_file_path,
    )
    image_generator.generate(theme)

    client.run(set_image(client))


if __name__ == '__main__':
    main()
