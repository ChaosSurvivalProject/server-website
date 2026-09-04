import { defineConfig } from 'vitepress'

export default defineConfig({
  title: '星穹旅驿 Wiki',
  description: '星穹旅驿服务器百科 - 服务器规则、玩法指南、常见问题',
  base: '/wiki/',

  themeConfig: {
    logo: '/logo.svg',
    nav: [
      { text: '首页', link: '/' },
      { text: '服务器规则', link: '/guide/rules' },
      { text: '玩法指南', link: '/guide/gameplay' },
      { text: '常见问题', link: '/faq' },
    ],
    sidebar: {
      '/guide/': [
        {
          text: '指南',
          items: [
            { text: '服务器规则', link: '/guide/rules' },
            { text: '玩法指南', link: '/guide/gameplay' },
            { text: '插件列表', link: '/guide/plugins' },
          ]
        }
      ],
      '/faq/': [
        {
          text: '常见问题',
          items: [
            { text: '常见问题', link: '/faq' },
          ]
        }
      ]
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/ChaosSurvivalProject' }
    ],
    footer: {
      message: '星穹旅驿 © 2025-2026',
      copyright: 'MIT Licensed'
    }
  }
})