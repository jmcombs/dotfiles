vim.pack.add({
    'https://github.com/nvim-treesitter/nvim-treesitter',
    'https://github.com/nvim-mini/mini.icons',
    'https://github.com/MeanderingProgrammer/render-markdown.nvim',
})

vim.schedule(function()
    -- nvim-treesitter v1.0+: the 'configs' module is gone.
    -- Highlighting and injections are now built into Neovim (0.10+).
    -- setup() only accepts { install_dir = '...' }; all other old options were removed.
    -- Run :TSInstall <lang> once to install parsers for fenced code block languages.
    local ok_ts, ts = pcall(require, 'nvim-treesitter')
    if ok_ts then
        ts.setup({})
    else
        vim.notify("nvim-treesitter not available: " .. ts, vim.log.levels.WARN)
    end

    local ok_icons, mini_icons = pcall(require, 'mini.icons')
    if ok_icons then
        mini_icons.setup({})
    end

    local ok_rm, rm = pcall(require, 'render-markdown')
    if ok_rm then
        rm.setup({
            code = {
                enabled = true,
                style = "full",
                width = "block",
                border = "thin",
            },
            latex = { enabled = false },
        })
    end
end)
