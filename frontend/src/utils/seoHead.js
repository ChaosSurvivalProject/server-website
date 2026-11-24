/**
 * FLPR-63：按路由注入独立的 head（title / description / canonical / OG / Twitter）。
 *
 * 关键约束：这些标签必须在构建期就写进静态 HTML。useHead() 在 vite-ssg 的
 * SSR 阶段执行，输出会随每页 index.html 一起落盘；浏览器端路由切换时同一段
 * 代码也会更新 head，不会出现「静态页有、切换后没有」的分叉。
 */
import { computed } from 'vue'
import { useHead } from '@unhead/vue'
import { useRoute } from 'vue-router'
import { siteBranding } from './siteBranding.js'
import { SHARE_COPY, DEFAULT_DESCRIPTION, composedTitle } from './shareMeta.js'

// 与 sitemap.xml / robots.txt / index.html 中的主域保持一致（唯一权威域名）。
// 全站 301 由网关归一到该主域，canonical 只写这一份。
const SITE_ORIGIN = 'https://xqly.xt91tv.shop'
const OG_IMAGE = `${SITE_ORIGIN}/og-cover.png`

// FLPR-64：全站结构化数据。WebSite + SearchAction 让引擎识别站点身份与站内搜索
// 入口（/forum?q= 是真实存在的搜索结果页，不是摆设）；FAQPage 在 /wiki/ 加入方式页。
const WEBSITE_JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: '星穹旅驿 我的世界阵营生存服',
  alternateName: '星穹旅驿',
  url: SITE_ORIGIN + '/',
  inLanguage: 'zh-CN',
  description: '我的世界 1.21 阵营服：Java / 基岩互通的 MC 双端互通服，黎明誓约与暮夜同盟阵营对抗，1.21.11 生存服。',
  potentialAction: {
    '@type': 'SearchAction',
    target: {
      '@type': 'EntryPoint',
      urlTemplate: SITE_ORIGIN + '/forum?q={search_term_string}'
    },
    'query-input': 'required name=search_term_string'
  }
}

export function useSeoHead() {
  const route = useRoute()

  useHead(computed(() => {
    const copy = SHARE_COPY[route.name] || SHARE_COPY.Home
    const siteName = siteBranding.name || '星穹旅驿'
    const title = composedTitle(copy.page, siteName)
    const description = copy.description || DEFAULT_DESCRIPTION
    // 归一：根路径保留斜杠，其余路径去掉尾部斜杠，避免 /team 与 /team/ 双份权重
    const path = (route.path || '/').replace(/\/+$/, '') || '/'
    const url = SITE_ORIGIN + path

    return {
      htmlAttrs: { lang: 'zh-CN' },
      title,
      meta: [
        { name: 'description', content: description },
        { property: 'og:type', content: 'website' },
        { property: 'og:site_name', content: siteName },
        { property: 'og:title', content: title },
        { property: 'og:description', content: description },
        { property: 'og:url', content: url },
        { property: 'og:image', content: OG_IMAGE },
        { property: 'og:image:secure_url', content: OG_IMAGE },
        { property: 'og:image:type', content: 'image/png' },
        { property: 'og:image:width', content: '1200' },
        { property: 'og:image:height', content: '630' },
        { property: 'og:image:alt', content: `${siteName} · 我的世界 1.21 阵营服 / Java 基岩互通 MC 双端互通服` },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:title', content: title },
        { name: 'twitter:description', content: description },
        { name: 'twitter:image', content: OG_IMAGE }
      ],
      link: [
        { rel: 'canonical', href: url }
      ],
      script: [
        {
          type: 'application/ld+json',
          innerHTML: JSON.stringify(WEBSITE_JSON_LD)
        }
      ]
    }
  }))
}
