import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "星穹旅驿Wiki",
  description: "星穹旅驿Wiki",
  base: '/wiki',
  themeConfig: {
    logo: '/favicon.ico',
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: '主页', link: '/' },
      // { text: '常见问题解答', link: '/for-new/faq/' },
      { text: '资源下载（网盘）', link: 'https://www.ilanzou.com/s/f6FnIguj', target: '_blank' },
      {
        text: '友情链接', items: [
          { text: '简幻欢—开服如此简单', link: 'https://simpfun.cn/auth?type=register&code=303249736', target: '_blank' },
          { text: '麦块联机—专业的Minecraft云服务器', link: 'https://minekuai.com/index/register?inviteCode=lwpnw2K', target: '_blank' },
          // { text: 'Floyd的导航站', link: 'https://floyd.tqclink.cn', target: '_blank' },
        ]
      },
    ],

    sidebar: {
      '/': [{
        text: '萌新指南',
        collapsed: false,
        items: [
          {
            text: '游玩须知', link: '/for-new/visitor-guidelines'
          },
          {
            text: '进服教程', collapsed: true, items: [
              { text: 'Java版', link: '/for-new/join-server/for-java-client/' },
              { text: '基岩版', link: '/for-new/join-server/for-bedrock-client/' }
            ]
          },
          {
            text: '服务器玩家相关条例', collapsed: true, items: [
              { text: '服务器游玩规则与惩罚条例', link: '/for-new/law/player-agreement' },
              { text: '服务器法典', link: '/for-new/law/server-code' },
              { text: '玩家维权与投诉处理条例', link: '/for-new/law/regulations-on-players-rights' }
            ]
          },
          {
            text: '常见问题解答', link: '/for-new/faq'
          },
        ]
      },
      {
        text: '服务器管理',
        collapsed: true,
        items: [
          { text: '服务器管理员监督问责条例', link: '/management/law-for-ops' },
        ]
      },
      {
        text: '服务器建设',
        collapsed: true,
        items: [
          { text: '发展路线', link: '/develop/roadmap' },
          { text: 'Issues', link: '/develop/issues' }
        ]
      }]
    },
    footer: {
      message: '联系邮箱: <a href="mailto:3896301937@qq.com">3896301937@qq.com</a>',
      copyright: 'Copyright © 2025 星穹旅驿 Minecraft服务器 | 本服务器与Mojang及Microsoft无关'
    },

    socialLinks: [
      { icon: 'qq', link: 'https://qun.qq.com/universal-share/share?ac=1&authKey=0SN/ztbeyrEd0N/ggnqVUgfEI3ap4vPTzNXpw46b4KsMNO%2B/jdG8hMC%2BZ0Ml7Hrh&busi_data=eyJncm91cENvZGUiOiI5NDIyMzU2OTEiLCJ0b2tlbiI6IkxlZWlUUkR1QXNTdWtzWDUzc09qRGp4TUtobEJXWU9CcmMwRzlUS2lUZUZ2QjhFWVJnSG93cjNoQnFQVFNpR1oiLCJ1aW4iOiIyMjgxNDYxMDU4In0=&data=UVH3Dw4afnupJPYfVA5NUCcoIuZQKcJVzrugaOe6sudIGlih_EqUnYhr6jN2nd0-q7GqsqG9_Cp7RtXj1irZmYKr_AcF1FWaU-2Vu0uhk5c&svctype=5&tempid=h5_group_info' },
    ]
  },
  cleanUrls: true,
  markdown: {
    toc: {}
  }
})
