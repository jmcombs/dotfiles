return {
    {
	"jmcombs/blue-psl-10k",
	lazy = false,
	priority = 1000,
	config = function()
	    require("blue-psl-10k").setup({
		transparent = true, -- seamless with the blue-psl-10k terminal background
	    })
	    vim.cmd.colorscheme("blue-psl-10k")
	end,
    },
    {
	"nvim-lualine/lualine.nvim",
	dependencies = {
	    "nvim-tree/nvim-web-devicons"
	},
	opts = {
	    theme = 'blue-psl-10k'
	},
    },
}
