import { defineConfig } from 'vitepress'

// FLPR-64：加入方式页 FAQPage。问答文本与 wiki/for-new/quick-start/index.md 正文一致。
// 通过 transformHead 注入而不是在 Markdown 里写 <script>——VitePress 会把 MD 中的
// script 当 SFC 脚本编译，直接写会构建失败。
const FAQ_JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: '星穹旅驿支持哪些客户端版本？',
      acceptedAnswer: {
        '@type': 'Answer',
        text: '星穹旅驿是我的世界 1.21 阵营服，支持 Minecraft Java 版与基岩版多端互通，Java 客户端版本 1.21.1 ~ 1.21.11（推荐 1.21.11），基岩版使用 1.21.x 最新正式版，服务端基于 Geyser + Velocity + Paper 1.21.11。'
      }
    },
    {
      '@type': 'Question',
      name: '星穹旅驿服务器地址是什么？基岩版怎么填？',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Java 版在多人游戏中添加服务器地址 serverone.codeyun.com:12000；基岩版在同服互通时把服务器地址填 serverone.codeyun.com、端口单独填 12000。连接成功后在登录服选择黎明誓约或暮夜同盟。'
      }
    },
    {
      '@type': 'Question',
      name: 'Java 版玩家怎么加入星穹旅驿？',
      acceptedAnswer: {
        '@type': 'Answer',
        text: '下载并安装 PCL2 等 Java 版启动器，选择 1.21.1 ~ 1.21.11 版本安装；进入多人游戏添加服务器 serverone.codeyun.com:12000；首次进入按提示用 /register 密码 重复密码 注册，老玩家用 /login 密码 登录，然后在登录服选择黎明誓约或暮夜同盟。'
      }
    },
    {
      '@type': 'Question',
      name: '基岩版 / 手机玩家怎么进服？',
      acceptedAnswer: {
        '@type': 'Answer',
        text: '安装 Minecraft Bedrock 基岩版最新正式版并登录微软账号，进入游戏服务器页添加服务器，地址填 serverone.codeyun.com、端口填 12000；连接后用 /register 或 /login 完成注册登录即可与 Java 玩家同服游玩。'
      }
    },
    {
      '@type': 'Question',
      name: '进服后怎么选择黎明誓约或暮夜同盟？',
      acceptedAnswer: {
        '@type': 'Answer',
        text: '连接服务器并完成注册或登录后，在登录服的选阵营界面选择黎明誓约或暮夜同盟。两大阵营镜像对立：黎明誓约以光为界、守土求生，暮夜同盟长夜将至、强者为尊。'
      }
    }
  ]
}

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "星穹旅驿 Wiki · 我的世界阵营生存服",
  description: "星穹旅驿 Wiki：我的世界 1.21 阵营服 / Java 基岩互通服务器文档，含进服指南、黎明誓约与暮夜同盟阵营玩法、1.21.11 生存服版本支持与服务器规则。",
  base: '/wiki',
  // 主题色与官网主站共用同一份 localStorage 派生变量（XQ_theme_vars_v2，v2 使旧缓存失效），
  // 首屏同步写入，避免 wiki 与主站主题色不一致。
  head: [
    ['script', {}, `(function(){try{var v=localStorage.getItem('XQ_theme_vars_v2');if(!v)return;var s=JSON.parse(v);var r=document.documentElement;for(var k in s){if(Object.prototype.hasOwnProperty.call(s,k))r.style.setProperty(k,s[k]);}}catch(e){}})();`],
    ['style', {}, `:root{--vp-c-brand-1:var(--brand-lt,#4caf50);--vp-c-brand-2:var(--brand-lt-hover,#43a047);--vp-c-brand-3:var(--brand-lt-active,#388e3c);--vp-c-brand-soft:var(--brand-lt-tint,#e8f5e9);}html.dark{--vp-c-brand-1:var(--brand-dk,#66bb6a);--vp-c-brand-2:var(--brand-dk-hover,#7bc87f);--vp-c-brand-3:var(--brand-dk-active,#55a55a);--vp-c-brand-soft:var(--brand-dk-tint,rgba(102,187,106,.16));}`],
    // 分享卡片：QQ / 微信抓取不执行 JS，OG 标签必须出现在服务器返回的原始 HTML 里。
    // VitePress 会把 head 原样写进每个静态页；og:image 复用主站根的封面图。
    // 按路由变化的 og:title / og:description / og:url 与 canonical 由 transformHead 注入。
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: '星穹旅驿 我的世界阵营生存服' }],
    ['meta', { name: 'description', content: '星穹旅驿 Wiki：我的世界 1.21 阵营服 / Java 基岩互通服务器文档，含进服指南、黎明誓约与暮夜同盟阵营玩法、1.21.11 生存服版本支持。' }],
    // FLPR-64：全站 WebSite + SearchAction，入口 /forum?q= 是官网真实搜索结果页。
    ['script', { type: 'application/ld+json' }, JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      name: '星穹旅驿 我的世界阵营生存服',
      alternateName: '星穹旅驿Wiki',
      url: 'https://xqly.xt91tv.shop/',
      inLanguage: 'zh-CN',
      description: '我的世界 1.21 阵营服：Java / 基岩互通的 MC 双端互通服，黎明誓约与暮夜同盟阵营对抗，1.21.11 生存服。',
      potentialAction: {
        '@type': 'SearchAction',
        target: { '@type': 'EntryPoint', urlTemplate: 'https://xqly.xt91tv.shop/forum?q={search_term_string}' },
        'query-input': 'required name=search_term_string'
      }
    })],
    ['meta', { property: 'og:image', content: 'https://xqly.xt91tv.shop/og-cover.png' }],
    ['meta', { property: 'og:image:width', content: '1200' }],
    ['meta', { property: 'og:image:height', content: '630' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:image', content: 'https://xqly.xt91tv.shop/og-cover.png' }]
  ],
  // FLPR-63：每页独立的 canonical / description / OG，构建期写进静态 HTML。
  // 站点描述是全局兜底，只在页面未写 description 时生成一段可读文案。
  transformHead: ({ page, title, description }) => {
    const rel = page.replace(/\.(html|md)$/, '').replace(/(^|\/)index$/, '$1').replace(/\/$/, '')
    const url = `https://xqly.xt91tv.shop/wiki/${rel ? `${rel}/` : ''}`
    const globalDescription = '星穹旅驿 Wiki · 我的世界阵营生存服'
    const pageDescription = description && description !== globalDescription
      ? description
      : `${title}：星穹旅驿我的世界 1.21 阵营服文档，包含 Java / 基岩互通进服指南、黎明誓约与暮夜同盟阵营玩法、1.21.11 生存服版本支持与服务器规则。`
    // VitePress 传入的 title 已带站点后缀，先剥掉再补统一品类后缀，避免两次拼接
    const siteTitleSuffix = '星穹旅驿 Wiki · 我的世界阵营生存服'
    const plainTitle = title.endsWith(siteTitleSuffix)
      ? title.slice(0, -siteTitleSuffix.length).replace(/\s*\|\s*$/, '')
      : title
    const pageTitle = `${plainTitle} | 星穹旅驿 我的世界阵营生存服`
    const head = [
      ['link', { rel: 'canonical', href: url }],
      ['meta', { name: 'description', content: pageDescription }],
      ['meta', { property: 'og:title', content: pageTitle }],
      ['meta', { property: 'og:description', content: pageDescription }],
      ['meta', { property: 'og:url', content: url }],
      ['meta', { name: 'twitter:title', content: pageTitle }],
      ['meta', { name: 'twitter:description', content: pageDescription }]
    ]
    // 只有加入方式页注入 FAQPage，避免把进服问答重复打到每页稀释权重
    if (page.replace(/\\/g, '/').endsWith('for-new/quick-start/index.md')) {
      head.push(['script', { type: 'application/ld+json' }, JSON.stringify(FAQ_JSON_LD)])
    }
    return head
  },
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
        text: '快速开始',
        collapsed: false,
        items: [
          { text: '进服指南（Java / 基岩并列）', link: '/for-new/quick-start/' },
          { text: '版本与客户端支持范围', link: '/for-new/versions/' },
          { text: '服务状态说明', link: '/about/service-status/' },
          { text: '活动与公告归档', link: '/about/announcements/' }
        ]
      },
      {
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
      copyright: '© 2025-2026 星穹旅驿 Minecraft 服务器 | 本服务器与Mojang及Microsoft无关'
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
