function get_ores(radius)
    local selection = game.player.selected
    if not selection or not selection.valid then
        game.print("No entity selected.")
        return
    end
    local entities = selection.surface.find_entities({
        {selection.position.x - radius, selection.position.y - radius},
        {selection.position.x + radius, selection.position.y + radius}
    })
    local ores = {}
    for _, entity in pairs(entities) do
        table.insert(ores, {
            name = entity.name,
            position = entity.position
        })
    end
    log(serpent.line(ores))
    helpers.write_file('ores.txt', serpent.line(ores))
end

get_ores(10)
