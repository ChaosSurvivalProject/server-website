<template>
  <section :id="id" class="card">
    <h2>{{ title }}</h2>
    <div v-if="content">
      <p v-html="content"></p>
    </div>
    <ul v-if="listItems && listItems.type === 'ul'">
      <li v-for="(item, index) in listItems.items" :key="index" v-html="item"></li>
    </ul>
    <ol v-if="listItems && listItems.type === 'ol'">
      <li v-for="(item, index) in listItems.items" :key="index" v-html="item"></li>
    </ol>
    <div v-if="footerContent">
      <p v-html="footerContent"></p>
    </div>
    <slot></slot>
  </section>
</template>

<script>
export default {
  name: 'ContentCard',
  props: {
    title: {
      type: String,
      required: true
    },
    content: {
      type: String,
      default: ''
    },
    listItems: {
      type: Object,
      default: null
    },
    footerContent: {
      type: String,
      default: ''
    },
    id: {
      type: String,
      default: ''
    }
  }
}
</script>

<style scoped>
.card {
  background-color: rgba(255, 255, 255, 0.95);
  padding: 20px;
  border: 4px solid var(--border-color);
}

.card h2 {
  font-size: 20px;
  margin-bottom: 15px;
  color: var(--primary-color);
  border-bottom: 3px solid var(--border-color);
  padding-bottom: 10px;
}

.card p, .card li {
  margin-bottom: 10px;
  line-height: 1.6;
}

.card ul, .card ol {
  margin-bottom: 15px;
  padding-left: 25px;
}

.card strong {
  font-weight: bold;
  color: var(--primary-color);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .card h2 {
    font-size: 16px;
  }
  
  .card p, .card li {
    font-size: 12px;
  }
}
</style>