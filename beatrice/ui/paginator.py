import discord


class EmbedPaginator(discord.ui.View):
    def __init__(self, pages: list[discord.Embed], owner_id: int, *, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.owner_id = owner_id
        self.index = 0
        self.interaction: discord.Interaction | None = None
        self._update_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.owner_id

    async def on_timeout(self) -> None:
        if self.interaction is None:
            return
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except discord.HTTPException:
            pass

    def _update_buttons(self) -> None:
        at_start = self.index == 0
        at_end = self.index == len(self.pages) - 1
        self.first.disabled = at_start
        self.previous.disabled = at_start
        self.next.disabled = at_end
        self.last.disabled = at_end
        self.indicator.label = f"{self.index + 1}/{len(self.pages)}"

    async def _show(self, interaction: discord.Interaction, index: int) -> None:
        self.index = index
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def first(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._show(interaction, 0)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._show(interaction, self.index - 1)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def indicator(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._show(interaction, self.index + 1)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def last(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._show(interaction, len(self.pages) - 1)


def build_pages(
    title: str,
    description: str,
    entries: list[tuple[str, str]],
    *,
    per_page: int = 10,
    colour: discord.Colour | None = None,
) -> list[discord.Embed]:
    colour = colour or discord.Colour.teal()
    pages = []
    for start in range(0, len(entries), per_page):
        embed = discord.Embed(title=title, description=description, colour=colour)
        for name, value in entries[start : start + per_page]:
            embed.add_field(name=name, value=value, inline=False)
        pages.append(embed)
    return pages


async def send_paginated(
    interaction: discord.Interaction,
    title: str,
    description: str,
    entries: list[tuple[str, str]],
    *,
    per_page: int = 10,
    colour: discord.Colour | None = None,
) -> None:
    pages = build_pages(title, description, entries, per_page=per_page, colour=colour)
    if len(pages) == 1:
        await interaction.response.send_message(embed=pages[0], ephemeral=True)
        return
    view = EmbedPaginator(pages, interaction.user.id)
    view.interaction = interaction
    await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)
