<template>
  <!--
    全局轻提示容器（挂一次即可，挂在 App.vue）。
    样式 .fx-toast 在 assets/styles/forum.css（全局，无需 scoped）。
  -->
  <div class="fx-toast" :class="{ show: state.visible }" role="status" aria-live="polite">
    {{ state.text }}
  </div>
</template>

<script>
import { forumToastState } from "../../utils/forumToast.js";

export default {
  name: "ForumToast",
  data() {
    return { state: forumToastState };
  },
};
</script>
