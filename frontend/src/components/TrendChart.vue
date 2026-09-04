<template>
  <div class="trend-header" id="trendHeader" style="font-size: 14px;">
    24小时在线人数 最后更新时间：{{ dataDate }}
  </div>
  <div class="trend-chart" id="trendChart">
    <!-- ECharts容器 -->
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script>
import * as echarts from 'echarts';

export default {
  name: 'TrendChart',
  props: {
    trendData: {
      type: Array,
      default: () => []
    },
    dataDate: {
      type: String,
      default: () => new Date().toLocaleDateString()
    }
  },
  data() {
    return {
      chart: null
    };
  },
  watch: {
    // 监听数据变化，重新渲染图表
    trendData: {
      handler() {
        this.updateChart();
      },
      deep: true
    }
  },
  mounted() {
    this.initChart();
    window.addEventListener('resize', this.handleResize);
  },
  beforeUnmount() {
    if (this.chart) {
      this.chart.dispose();
      this.chart = null;
    }
    window.removeEventListener('resize', this.handleResize);
  },
  methods: {
    // 初始化ECharts实例
    initChart() {
      this.chart = echarts.init(this.$refs.chartContainer);
      this.updateChart();
    },
    // 更新图表数据和配置
    updateChart() {
      if (!this.chart || !this.trendData || this.trendData.length === 0) return;
      
      // 准备数据
      const xAxisData = this.trendData.map(item => item.hour);
      const seriesData = this.trendData.map(item => item.count);
      
      // 获取响应式配置
      const responsiveConfig = this.getResponsiveConfig();
      
      // 图表配置
        const option = {
          // 添加标题，显示统计日期
          title: {
            text: '',
            left: 'center'
          },
          // 工具箱，提供一些交互功能
          toolbox: {
            show: responsiveConfig.toolbox.show,
            feature: {
              saveAsImage: {
                title: '保存图片',
                show: responsiveConfig.toolbox.feature.saveAsImage.show
              },
              dataView: {
                title: '数据视图',
                readOnly: true,
                show: responsiveConfig.toolbox.feature.dataView.show
              },
              restore: {
                title: '重置',
                show: responsiveConfig.toolbox.feature.restore.show
              }
            },
            right: responsiveConfig.toolbox.right,
            top: responsiveConfig.toolbox.top,
            iconStyle: {
              borderColor: '#666'
            },
            iconSize: responsiveConfig.toolbox.iconSize
          },
          // 提示框配置
          tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            borderColor: '#333',
            textStyle: {
              color: '#fff'
            },
            axisPointer: {
              type: 'line',
              lineStyle: {
                color: '#4CAF50',
                width: 2,
                type: 'dashed'
              }
            },
            formatter: function(params) {
              const data = params[0];
              return `${data.axisValue}<br/>在线人数：<strong style="color: #4CAF50;">${data.value}人</strong>`;
            }
          },
          // 网格配置
          grid: {
            left: responsiveConfig.grid.left,
            right: responsiveConfig.grid.right,
            bottom: responsiveConfig.grid.bottom,
            top: responsiveConfig.grid.top,
            containLabel: responsiveConfig.grid.containLabel,
            borderColor: '#eee'
          },
          // X轴配置
          xAxis: {
            type: 'category',
            boundaryGap: false,
            data: xAxisData,
            axisLine: {
              lineStyle: {
                color: '#999'
              }
            },
            axisLabel: {
              color: '#666',
              rotate: responsiveConfig.xAxis.axisLabel.rotate,
              interval: responsiveConfig.xAxis.axisLabel.interval,
              fontSize: responsiveConfig.xAxis.axisLabel.fontSize,
              formatter: function(value) {
                // 简化时间显示
                return value.replace(':00', '');
              }
            },
            splitLine: {
              show: true,
              lineStyle: {
                type: 'dashed',
                color: '#eee'
              }
            }
          },
          // Y轴配置
          yAxis: {
            type: 'value',
            name: '在线人数',
            nameTextStyle: {
              color: '#666'
            },
            min: 0,
            axisLine: {
              show: true,
              lineStyle: {
                color: '#999'
              }
            },
            axisLabel: {
              color: '#666',
              fontSize: responsiveConfig.yAxis.axisLabel.fontSize,
              formatter: '{value}人'
            },
            splitLine: {
              lineStyle: {
                type: 'dashed',
                color: '#eee'
              }
            }
          },
          // 数据系列配置
          series: [
            {
              name: '在线人数',
              type: 'line',
              data: seriesData,
              smooth: true,
              // 动画效果
              animationDuration: 1000,
              animationEasing: 'cubicOut',
              // 线条样式
              lineStyle: {
                width: responsiveConfig.series.lineStyle.width,
                color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: '#4CAF50' },
                  { offset: 1, color: '#8BC34A' }
                ])
              },
              // 区域填充样式
              areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: 'rgba(76, 175, 80, 0.5)' },
                  { offset: 1, color: '#4CAF50' }
                ])
              },
              // 数据点样式
              itemStyle: {
                color: '#4CAF50',
                borderWidth: responsiveConfig.series.itemStyle.borderWidth,
                borderColor: '#fff',
                shadowColor: 'rgba(76, 175, 80, 0.5)',
                shadowBlur: responsiveConfig.series.itemStyle.shadowBlur
              },
              // 鼠标悬停时的数据点样式
              emphasis: {
                itemStyle: {
                  color: '#ff6600',
                  borderWidth: 3,
                  borderColor: '#fff',
                  shadowColor: 'rgba(255, 102, 0, 0.8)',
                  shadowBlur: 10
                }
              },
              // 标记点（最大值、最小值）
              markPoint: {
                show: responsiveConfig.series.markPoint.show,
                data: [
                  { type: 'max', name: '最大在线人数' },
                  { type: 'min', name: '最小在线人数' }
                ],
                label: {
                  color: '#666'
                },
                itemStyle: {
                  color: '#ff6600'
                }
              },
              // 标记线（平均值）
              markLine: {
                show: responsiveConfig.series.markLine.show,
                data: [
                  { type: 'average', name: '平均在线人数' }
                ],
                lineStyle: {
                  color: '#999',
                  type: 'dashed'
                },
                label: {
                  color: '#666'
                }
              }
            }
          ],
          // 视觉映射，增强数据可视化效果
          visualMap: {
            show: false,
            dimension: 0,
            seriesIndex: 0,
            min: 0,
            max: seriesData.length - 1,
            inRange: {
              colorLightness: [0.3, 1]
            }
          }
        };
      
      this.chart.setOption(option);
    },
    // 处理窗口大小变化
      handleResize() {
        if (this.chart) {
          // 先调整图表尺寸
          this.chart.resize();
          
          // 然后重新设置图表选项，确保响应式配置生效
          this.updateChart();
        }
      },
      
      // 获取当前窗口的响应式配置
      getResponsiveConfig() {
        const isMobile = window.innerWidth < 768;
        const isSmallMobile = window.innerWidth < 480;
        
        return {
          // 工具箱配置
          toolbox: {
            show: !isSmallMobile,
            feature: {
              saveAsImage: {
                show: !isSmallMobile
              },
              dataView: {
                show: !isSmallMobile
              },
              restore: {
                show: !isSmallMobile
              }
            },
            right: 10,
            top: 10,
            iconSize: isMobile ? 15 : 20
          },
          
          // 网格配置
          grid: {
            left: '3%',
            right: isMobile ? '5%' : '4%',
            bottom: isMobile ? '20%' : '15%',
            top: isSmallMobile ? '10%' : '15%',
            containLabel: true
          },
          
          // X轴配置
          xAxis: {
            axisLabel: {
              rotate: isMobile ? 45 : 0,
              interval: isMobile ? 2 : 0,
              fontSize: isSmallMobile ? 10 : (isMobile ? 12 : 14)
            }
          },
          
          // Y轴配置
          yAxis: {
            axisLabel: {
              fontSize: isSmallMobile ? 10 : (isMobile ? 12 : 14)
            }
          },
          
          // 系列配置
          series: {
            lineStyle: {
              width: isSmallMobile ? 2 : 3
            },
            itemStyle: {
              borderWidth: isSmallMobile ? 1 : 2,
              shadowBlur: isSmallMobile ? 3 : 5
            },
            // 在小屏幕上减少标记点和标记线，避免过于拥挤
            markPoint: {
              show: !isSmallMobile
            },
            markLine: {
              show: !isSmallMobile
            }
          }
        };
      }
  }
}
</script>

<style scoped>
.trend-header {
  font-size: 16px;
  font-weight: bold;
  color: var(--primary-color);
  text-align: right;
  cursor: default;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 5px 0;
  margin-bottom: 10px;
  transition: background-color 0.2s ease;
}

.trend-chart {
  height: 250px;
  position: relative;
  border: 2px solid var(--border-color);
  background-color: rgba(255, 255, 255, 0.95);
  padding: 10px;
  overflow: hidden;
}

.chart-container {
  width: 100%;
  height: 100%;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .trend-chart {
    height: 200px;
  }
}

/* 确保图表在移动设备上有更好的显示效果 */
@media (max-width: 480px) {
  .trend-chart {
    height: 180px;
    padding: 5px;
  }
  
  .trend-header {
    font-size: 14px;
  }
}
</style>