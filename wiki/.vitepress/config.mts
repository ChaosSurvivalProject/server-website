import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "星穹旅驿Wiki",
  description: "星穹旅驿Wiki",
  base: '/wiki',
  // 主题色与官网主站共用同一份 localStorage 派生变量（XQ_theme_vars_v2，v2 使旧缓存失效），
  // 首屏同步写入，避免 wiki 与主站主题色不一致。
  head: [
    ['script', {}, `(function(){try{var v=localStorage.getItem('XQ_theme_vars_v2');if(!v)return;var s=JSON.parse(v);var r=document.documentElement;for(var k in s){if(Object.prototype.hasOwnProperty.call(s,k))r.style.setProperty(k,s[k]);}}catch(e){}})();`],
    ['style', {}, `:root{--vp-c-brand-1:var(--brand-lt,#4caf50);--vp-c-brand-2:var(--brand-lt-hover,#43a047);--vp-c-brand-3:var(--brand-lt-active,#388e3c);--vp-c-brand-soft:var(--brand-lt-tint,#e8f5e9);}html.dark{--vp-c-brand-1:var(--brand-dk,#66bb6a);--vp-c-brand-2:var(--brand-dk-hover,#7bc87f);--vp-c-brand-3:var(--brand-dk-active,#55a55a);--vp-c-brand-soft:var(--brand-dk-tint,rgba(102,187,106,.16));}`],
    // 分享卡片：QQ / 微信抓取不执行 JS，OG 标签必须出现在服务器返回的原始 HTML 里。
    // VitePress 会把 head 原样写进每个静态页；og:image 复用主站根的封面图。
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: '星穹旅驿Wiki' }],
    ['meta', { property: 'og:title', content: '星穹旅驿Wiki | 我的世界阵营生存服文档' }],
    ['meta', { property: 'og:description', content: '星穹旅驿 Wiki：进服指南、Java / 基岩双端教程、黎明誓约与暮夜同盟阵营玩法、服务器规则与架构文档。' }],
    ['meta', { property: 'og:url', content: 'https://xqly.xt91tv.shop/wiki/' }],
    ['meta', { property: 'og:image', content: 'https://xqly.xt91tv.shop/og-cover.png' }],
    ['meta', { property: 'og:image:width', content: '1200' }],
    ['meta', { property: 'og:image:height', content: '630' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:title', content: '星穹旅驿Wiki | 我的世界阵营生存服文档' }],
    ['meta', { name: 'twitter:description', content: '星穹旅驿 Wiki：进服指南、Java / 基岩双端教程、黎明誓约与暮夜同盟阵营玩法、服务器规则与架构文档。' }],
    ['meta', { name: 'twitter:image', content: 'https://xqly.xt91tv.shop/og-cover.png' }]
  ],
  themeConfig: {
    logo: '/favicon.ico',
    // 文档站跟随 VitePress 内置的三态外观切换（自动 / 浅色 / 深色），
    // 与主站一样支持系统偏好与持久化。
    appearance: true,
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
            text: '阵营玩法', collapsed: true, items: [
              { text: '阵营玩法总览', link: '/for-new/factions/' },
              { text: '阵营使用指南', link: '/for-new/factions/usage' },
              { text: '阵营对抗机制', link: '/for-new/factions/mechanics' }
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
          { text: '服务器架构', link: '/develop/architecture' },
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
