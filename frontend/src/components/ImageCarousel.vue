<template>
  <div class="carousel-container">
    <div class="carousel-wrapper" :style="{ transform: `translateX(-${currentIndex * 100}%)` }">
      <div 
        v-for="(image, index) in images" 
        :key="index"
        class="carousel-slide"
      >
        <img :src="image.src" :alt="image.alt" class="carousel-image" />
      </div>
    </div>
    <div class="carousel-controls">
      <button 
        class="carousel-control-prev" 
        @click="prevSlide"
        aria-label="Previous"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>
      <button 
        class="carousel-control-next" 
        @click="nextSlide"
        aria-label="Next"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>
    </div>
    <div class="carousel-indicators">
      <button 
        v-for="(image, index) in images" 
        :key="index"
        class="carousel-indicator"
        :class="{ active: index === currentIndex }"
        @click="goToSlide(index)"
        :aria-label="`Slide ${index + 1}`"
      ></button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ImageCarousel',
  props: {
    images: {
      type: Array,
      required: true,
      default: () => []
    },
    interval: {
      type: Number,
      default: 5000
    },
    autoplay: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      currentIndex: 0,
      autoplayTimer: null
    };
  },
  mounted() {
    if (this.autoplay) {
      this.startAutoplay();
    }
  },
  beforeUnmount() {
    this.stopAutoplay();
  },
  methods: {
    nextSlide() {
      this.currentIndex = (this.currentIndex + 1) % this.images.length;
      this.resetAutoplay();
    },
    prevSlide() {
      this.currentIndex = (this.currentIndex - 1 + this.images.length) % this.images.length;
      this.resetAutoplay();
    },
    goToSlide(index) {
      this.currentIndex = index;
      this.resetAutoplay();
    },
    startAutoplay() {
      this.autoplayTimer = setInterval(() => {
        this.nextSlide();
      }, this.interval);
    },
    stopAutoplay() {
      if (this.autoplayTimer) {
        clearInterval(this.autoplayTimer);
        this.autoplayTimer = null;
      }
    },
    resetAutoplay() {
      if (this.autoplay) {
        this.stopAutoplay();
        this.startAutoplay();
      }
    }
  }
};
</script>

<style scoped>
.carousel-container {
  position: relative;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  overflow: hidden;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.carousel-wrapper {
  display: flex;
  transition: transform 0.5s ease;
  height: 100%;
}

.carousel-slide {
  flex: 0 0 100%;
  /* height: 600px; */
}

.carousel-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.carousel-controls {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  transform: translateY(-50%);
  display: flex;
  justify-content: space-between;
  padding: 0 20px;
}

.carousel-control-prev,
.carousel-control-next {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.8);
  color: #333;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.carousel-control-prev:hover,
.carousel-control-next:hover {
  background-color: rgba(255, 255, 255, 1);
  transform: scale(1.1);
}

.carousel-indicators {
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  gap: 8px;
}

.carousel-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.5);
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.carousel-indicator.active {
  background-color: white;
  width: 32px;
  border-radius: 6px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .carousel-container {
    max-width: 100%;
  }
  
  .carousel-slide {
    height: 250px;
  }
  
  .carousel-control-prev,
  .carousel-control-next {
    width: 32px;
    height: 32px;
  }
  
  .carousel-control-prev svg,
  .carousel-control-next svg {
    width: 16px;
    height: 16px;
  }
}
</style>