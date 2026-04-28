import React, { useEffect, useState } from 'react'
import { List, Card, Button, Tag, Checkbox, Input, Select, Spin, Alert, Popconfirm, Typography, Space, Progress, Divider, message, DatePicker, Slider, Drawer, Modal, Form } from 'antd'
import { DeleteOutlined, SearchOutlined, ClockCircleOutlined, ThunderboltOutlined, EditOutlined, FilterOutlined, SaveOutlined } from '@ant-design/icons'
import { useTaskStore } from '../store/taskStore'
import { TaskStatus, TaskPriority, Task, FilterPreset } from '../types/task'
import TaskEditModal from './TaskEditModal'
import { taskApi, API_URL } from '../api/taskApi'

const { Option } = Select
const { RangePicker } = DatePicker
const { Title, Text } = Typography

const TaskList: React.FC = () => {
  const { tasks, fetchTasks, updateTaskStatus, deleteTask, updateSubTaskStatus, updateTaskProgress, loading, error } = useTaskStore()
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [filterPriority, setFilterPriority] = useState<string>('')
  const [filterCategory, setFilterCategory] = useState<string>('')
  const [filterTag, setFilterTag] = useState<string>('')
  const [dateRange, setDateRange] = useState<[string, string] | null>(null)
  const [progressRange, setProgressRange] = useState<[number, number]>([0, 100])
  const [searchKeyword, setSearchKeyword] = useState<string>('')
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [sortBy, setSortBy] = useState<string>('create_time')
  const [advancedFilterVisible, setAdvancedFilterVisible] = useState(false)
  const [categories, setCategories] = useState<{id: number, name: string}[]>([])
  const [tags, setTags] = useState<{id: number, name: string}[]>([])
  const [filterPresets, setFilterPresets] = useState<FilterPreset[]>([])

  useEffect(() => {
    fetchTasks()
    fetchCategories()
    fetchTags()
    fetchFilterPresets()
  }, [fetchTasks])

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/categories`)
      const data = await response.json()
      if (data.success) {
        setCategories(data.categories || [])
      }
    } catch (error) {
      console.error('获取分类失败', error)
    }
  }

  const fetchTags = async () => {
    try {
      const response = await fetch(`${API_URL}/tags`)
      const data = await response.json()
      if (data.success) {
        setTags(data.tags || [])
      }
    } catch (error) {
      console.error('获取标签失败', error)
    }
  }

  const resetFilters = () => {
    setFilterStatus('')
    setFilterPriority('')
    setFilterCategory('')
    setFilterTag('')
    setDateRange(null)
    setProgressRange([0, 100])
    setSearchKeyword('')
  }

  const applyPreset = (preset: FilterPreset) => {
    setFilterStatus(preset.filters.status || '')
    setFilterPriority(preset.filters.priority || '')
    setFilterCategory(preset.filters.category || '')
    setFilterTag(preset.filters.tag || '')
    setDateRange(preset.filters.dateRange || null)
    setProgressRange(preset.filters.progressRange || [0, 100])
  }

  const getCurrentFilters = (): FilterPreset['filters'] => ({
    status: filterStatus || undefined,
    priority: filterPriority || undefined,
    category: filterCategory || undefined,
    tag: filterTag || undefined,
    dateRange: dateRange || undefined,
    progressRange: progressRange
  })

  const handleStatusChange = (taskId: number, status: TaskStatus) => {
    updateTaskStatus(taskId, status)
  }

  const handleDelete = (taskId: number) => {
    deleteTask(taskId)
  }

  const handleEdit = (task: Task) => {
    setEditingTask(task)
    setEditModalOpen(true)
  }

  const handleCloseEditModal = () => {
    setEditModalOpen(false)
    setEditingTask(null)
  }

  const handleSubTaskToggle = (taskId: number, subTaskIndex: number, completed: boolean) => {
    updateSubTaskStatus(taskId, subTaskIndex, completed)
  }

  const handleExport = () => {
    if (filteredTasks.length === 0) {
      message.info('暂无任务可导出')
      return
    }

    const exportData = filteredTasks.map(task => ({
      id: task.id,
      任务名称: task.raw_task || '无',
      优先级: task.priority || '无',
      状态: task.status || '无',
      截止日期: task.deadline && task.deadline !== 'null' ? task.deadline : '无',
      完成进度: `${typeof task.progress === 'number' ? task.progress : 0}%`,
      分类: task.category || '无',
      标签: task.tags && Array.isArray(task.tags) ? task.tags.join(', ') : '无',
      子任务: task.sub_tasks && Array.isArray(task.sub_tasks) ? task.sub_tasks.map(st => `${st.completed ? '✓' : '✗'} ${st.text}`).join('\n') : '无',
      备注: task.notes || '无',
      创建时间: task.create_time || '无',
      更新时间: task.update_time || '无'
    }))

    // 导出为CSV
    const csvContent = [
      Object.keys(exportData[0]).join(','),
      ...exportData.map(row => Object.values(row).map(value => `"${String(value).replace(/"/g, '""')}"`).join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', `任务导出_${new Date().toISOString().slice(0, 10)}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }
  }

  // 筛选预设相关函数
  const [presetModalVisible, setPresetModalVisible] = useState(false)
  const [presetName, setPresetName] = useState('')
  const [editingPreset, setEditingPreset] = useState<FilterPreset | null>(null)
  const [presetForm] = Form.useForm()

  const fetchFilterPresets = async () => {
    try {
      const response = await taskApi.getFilterPresets()
      setFilterPresets(response.data || [])
    } catch (error) {
      console.error('获取筛选预设失败', error)
    }
  }

  const handleSavePreset = async () => {
    try {
      const values = await presetForm.validateFields()
      const filters = getCurrentFilters()
      
      let response
      if (editingPreset && editingPreset.id) {
        response = await taskApi.updateFilterPreset(editingPreset.id, { 
          name: values.name, 
          filters 
        })
        message.success('筛选预设更新成功')
      } else {
        response = await taskApi.createFilterPreset({ 
          name: values.name, 
          filters 
        })
        message.success('筛选预设保存成功')
      }

      if (response.data.success) {
        setPresetModalVisible(false)
        setEditingPreset(null)
        presetForm.resetFields()
        fetchFilterPresets()
      }
    } catch (error) {
      console.error('保存筛选预设失败', error)
      message.error('保存筛选预设失败')
    }
  }

  const handleEditPreset = (preset: FilterPreset) => {
    setEditingPreset(preset)
    presetForm.setFieldsValue({ name: preset.name })
    setPresetModalVisible(true)
  }

  const handleDeletePreset = async (presetId: number) => {
    try {
      const response = await taskApi.deleteFilterPreset(presetId)
      if (response.data.success) {
        message.success('筛选预设删除成功')
        fetchFilterPresets()
      }
    } catch (error) {
      console.error('删除筛选预设失败', error)
      message.error('删除筛选预设失败')
    }
  }

  const getPriorityValue = (priority: TaskPriority) => {
    switch (priority) {
      case '高': return 3
      case '中': return 2
      case '低': return 1
      default: return 0
    }
  }

  const getStatusValue = (status: TaskStatus) => {
    switch (status) {
      case '待执行': return 1
      case '进行中': return 2
      case '已完成': return 3
      case '已过期': return 0
      default: return 0
    }
  }

  const getPriorityColor = (priority: TaskPriority) => {
    switch (priority) {
      case '高': return 'red'
      case '中': return 'orange'
      case '低': return 'green'
      default: return 'blue'
    }
  }

  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case '待执行': return 'blue'
      case '进行中': return 'orange'
      case '已完成': return 'green'
      case '已过期': return 'red'
      default: return 'default'
    }
  }

  const getPriorityClass = (priority: TaskPriority) => {
    switch (priority) {
      case '高': return 'priority-high'
      case '中': return 'priority-medium'
      case '低': return 'priority-low'
      default: return ''
    }
  }

  const filteredTasks = tasks
    .filter(task => {
      // Handle null/undefined values
      if (!task) return false
      
      const matchesStatus = !filterStatus || task.status === filterStatus
      const matchesPriority = !filterPriority || task.priority === filterPriority
      const matchesCategory = !filterCategory || task.category === filterCategory
      const matchesTag = !filterTag || (task.tags && task.tags.includes(filterTag))
      const matchesKeyword = !searchKeyword ||
        (task.raw_task && task.raw_task.includes(searchKeyword)) ||
        (task.sub_tasks && Array.isArray(task.sub_tasks) && task.sub_tasks.some(subTask => subTask.text && subTask.text.includes(searchKeyword)))
      const matchesDateRange = !dateRange || (
        task.deadline && task.deadline !== 'null' &&
        task.deadline >= dateRange[0] &&
        task.deadline <= dateRange[1]
      )
      // Handle progress as number or string
      const progress = typeof task.progress === 'number' ? task.progress : 0
      const matchesProgress = progress >= progressRange[0] && progress <= progressRange[1]
      return matchesStatus && matchesPriority && matchesCategory && matchesTag && matchesKeyword && matchesDateRange && matchesProgress
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'priority':
          return getPriorityValue(b.priority) - getPriorityValue(a.priority)
        case 'deadline':
          if (!a.deadline || a.deadline === 'null') return 1
          if (!b.deadline || b.deadline === 'null') return -1
          return a.deadline.localeCompare(b.deadline)
        case 'progress':
          const progressA = typeof a.progress === 'number' ? a.progress : 0
          const progressB = typeof b.progress === 'number' ? b.progress : 0
          return progressB - progressA
        case 'status':
          return getStatusValue(a.status) - getStatusValue(b.status)
        case 'create_time':
        default:
          return (b.create_time || '').localeCompare(a.create_time || '')
      }
    })

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}><Spin size="large" /></div>
  }

  if (error) {
    return <Alert message="错误" description={error} type="error" showIcon />
  }

  return (
    <div className="page-section">
      <div className="page-hero">
        <Text className="page-hero-kicker">Task Center</Text>
        <Title level={3} className="page-hero-title">
          把任务、优先级和进度整理得更清楚
        </Title>
        <Text className="page-hero-description">
          支持按关键字、状态和优先级快速筛选，适合集中处理一批任务或追踪当前进展。
        </Text>
      </div>

      <Card className="glass-card">
        <div className="toolbar-row">
          <Input
            className="toolbar-search"
            placeholder="搜索任务名称或子任务"
            prefix={<SearchOutlined />}
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
          />
          <Select
            placeholder="按状态筛选"
            value={filterStatus || undefined}
            onChange={(value) => setFilterStatus(value || '')}
            allowClear
          >
            <Option value="待执行">待执行</Option>
            <Option value="进行中">进行中</Option>
            <Option value="已完成">已完成</Option>
            <Option value="已过期">已过期</Option>
          </Select>
          <Select
            placeholder="按优先级筛选"
            value={filterPriority || undefined}
            onChange={(value) => setFilterPriority(value || '')}
            allowClear
          >
            <Option value="高">高</Option>
            <Option value="中">中</Option>
            <Option value="低">低</Option>
          </Select>
          <Select
            placeholder="排序方式"
            value={sortBy}
            onChange={(value) => setSortBy(value)}
          >
            <Option value="create_time">创建时间</Option>
            <Option value="priority">优先级</Option>
            <Option value="deadline">截止日期</Option>
            <Option value="progress">完成进度</Option>
            <Option value="status">任务状态</Option>
          </Select>
          <Select
            placeholder="筛选预设"
            style={{ width: 180 }}
            dropdownRender={menu => (
              <div>
                {menu}
                <Divider style={{ margin: '8px 0' }} />
                <div style={{ padding: '0 8px 8px 8px' }}>
                  <Button 
                    type="text" 
                    style={{ width: '100%', textAlign: 'left' }}
                    icon={<SaveOutlined />}
                    onClick={() => {
                      setEditingPreset(null)
                      presetForm.resetFields()
                      setPresetModalVisible(true)
                    }}
                  >
                    保存当前筛选
                  </Button>
                </div>
              </div>
            )}
            onSelect={(value: string) => {
              if (value !== 'save') {
                const preset = filterPresets.find(p => p.id === parseInt(value))
                if (preset) {
                  applyPreset(preset)
                }
              }
            }}
            labelRender={(props) => {
              if (props.value === 'save') {
                return <span>保存当前筛选</span>
              }
              const preset = filterPresets.find(p => p.id === parseInt(props.value))
              if (!preset) return <span>{props.label}</span>
              return (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{preset.name}</span>
                  <Space size="small">
                    <Button 
                      type="text" 
                      size="small"
                      icon={<EditOutlined />}
                      onClick={(e) => {
                        e.stopPropagation()
                        handleEditPreset(preset)
                      }}
                    />
                    <Popconfirm
                      title="确定删除此筛选预设?"
                      onConfirm={(e) => {
                        e?.stopPropagation()
                        if (preset.id) {
                          handleDeletePreset(preset.id)
                        }
                      }}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button 
                        type="text" 
                        danger 
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </Popconfirm>
                  </Space>
                </div>
              )
            }}
          >
            {filterPresets.map(preset => (
              <Option key={preset.id || Math.random()} value={(preset.id || 0).toString()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{preset.name}</span>
                  <Space size="small">
                    <Button 
                      type="text" 
                      size="small"
                      icon={<EditOutlined />}
                      onClick={(e) => {
                        e.stopPropagation()
                        handleEditPreset(preset)
                      }}
                    />
                    <Popconfirm
                      title="确定删除此筛选预设?"
                      onConfirm={(e) => {
                        e?.stopPropagation()
                        if (preset.id) {
                          handleDeletePreset(preset.id)
                        }
                      }}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button 
                        type="text" 
                        danger 
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </Popconfirm>
                  </Space>
                </div>
              </Option>
            ))}
          </Select>
          <Button
            icon={<FilterOutlined />}
            onClick={() => setAdvancedFilterVisible(true)}
          >
            高级筛选
          </Button>
          <Button
            type="primary"
            onClick={() => handleExport()}
          >
            导出任务
          </Button>
        </div>
      </Card>

      <Drawer
        title="高级筛选"
        placement="right"
        onClose={() => setAdvancedFilterVisible(false)}
        open={advancedFilterVisible}
        width={360}
        extra={
          <Space>
            <Button onClick={resetFilters}>重置</Button>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text strong>按分类筛选</Text>
            <Select
              style={{ width: '100%', marginTop: 8 }}
              placeholder="选择分类"
              value={filterCategory || undefined}
              onChange={(value) => setFilterCategory(value || '')}
              allowClear
            >
              {categories.map(cat => (
                <Option key={cat.id} value={cat.name}>{cat.name}</Option>
              ))}
            </Select>
          </div>

          <div>
            <Text strong>按标签筛选</Text>
            <Select
              style={{ width: '100%', marginTop: 8 }}
              placeholder="选择标签"
              value={filterTag || undefined}
              onChange={(value) => setFilterTag(value || '')}
              allowClear
            >
              {tags.map(tag => (
                <Option key={tag.id} value={tag.name}>{tag.name}</Option>
              ))}
            </Select>
          </div>

          <div>
            <Text strong>按日期范围筛选</Text>
            <RangePicker
              style={{ width: '100%', marginTop: 8 }}
              onChange={(_, dateStrings) => {
                if (dateStrings[0] && dateStrings[1]) {
                  setDateRange([dateStrings[0], dateStrings[1]])
                } else {
                  setDateRange(null)
                }
              }}
            />
          </div>

          <div>
            <Text strong>按进度范围筛选: {progressRange[0]}% - {progressRange[1]}%</Text>
            <Slider
              range
              min={0}
              max={100}
              value={progressRange}
              onChange={(value) => setProgressRange(value as [number, number])}
              marks={{ 0: '0%', 50: '50%', 100: '100%' }}
              style={{ marginTop: 8 }}
            />
          </div>

          <Button block type="primary" onClick={() => setAdvancedFilterVisible(false)}>
            应用筛选
          </Button>
        </Space>
      </Drawer>

      <Card className="surface-card">
        <Space direction="vertical" size={6} style={{ width: '100%', marginBottom: 8 }}>
          <Title level={4} className="section-title">
            当前结果
          </Title>
          <Text className="section-subtitle">
            共找到 {filteredTasks.length} 个任务，可直接勾选完成或切换状态。
          </Text>
        </Space>

        <List
          itemLayout="vertical"
          dataSource={filteredTasks}
          renderItem={(task) => (
            <List.Item key={task.id} style={{ paddingInline: 0, borderBlockEnd: 0 }}>
              <Card className={`task-card ${getPriorityClass(task.priority)}`}>
                <div className="task-title-row">
                  <div className="task-title-main">
                    <Checkbox
                      checked={task.status === '已完成'}
                      onChange={(e) => handleStatusChange(task.id, e.target.checked ? '已完成' : '待执行')}
                      style={{ marginTop: 4 }}
                    />
                    <div style={{ flex: 1 }}>
                      <Text
                        strong
                        className="task-title-text"
                        delete={task.status === '已完成'}
                        style={{ fontSize: 18, marginBottom: 12 }}
                      >
                        {task.raw_task}
                      </Text>
                      <div className="task-chip-row">
                        <Tag icon={<ThunderboltOutlined />} color={getPriorityColor(task.priority)}>
                          {task.priority}优先级
                        </Tag>
                        <Tag color={getStatusColor(task.status)}>
                          {task.status}
                        </Tag>
                        {task.category && <Tag color="geekblue">{task.category}</Tag>}
                      </div>
                    </div>
                  </div>
                  <div className="task-meta-block">
                    <Space direction="vertical" align="end" size={4}>
                      <Text className="task-meta-text" style={{ fontSize: 13 }}>
                        <ClockCircleOutlined style={{ marginRight: 6 }} />
                        截止: {task.deadline && task.deadline !== 'null' ? task.deadline : '无'}
                      </Text>
                      <div style={{ width: 150, marginTop: 8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <Text type="secondary" style={{ fontSize: 12 }}>完成度</Text>
                          <Text strong style={{ fontSize: 12 }}>{typeof task.progress === 'number' ? task.progress : 0}%</Text>
                        </div>
                        <Progress 
                          percent={typeof task.progress === 'number' ? task.progress : 0} 
                          size="small" 
                          showInfo={false}
                          strokeColor={{
                            '0%': '#5b7cff',
                            '100%': '#16c784',
                          }}
                        />
                        <div style={{ marginTop: 8 }}>
                          <Slider
                            min={0}
                            max={100}
                            value={typeof task.progress === 'number' ? task.progress : 0}
                            onChange={(value) => updateTaskProgress(task.id, value)}
                            style={{ width: '100%' }}
                            tooltip={{ formatter: (value) => `${value}%` }}
                          />
                        </div>
                      </div>
                    </Space>
                  </div>
                </div>

                {task.sub_tasks && Array.isArray(task.sub_tasks) && task.sub_tasks.length > 0 && (
                  <div style={{ marginTop: 24, padding: '16px', background: 'rgba(248, 250, 252, 0.6)', borderRadius: 16 }}>
                    <Title level={5} style={{ marginBottom: 16, fontSize: 14, color: 'var(--text-secondary)' }}>
                      拆解子任务 ({task.sub_tasks.filter(st => st.completed).length}/{task.sub_tasks.length})
                    </Title>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
                      {task.sub_tasks.map((subTask, index) => (
                        <div key={index} className="sub-task" style={{ margin: 0 }}>
                          <Checkbox 
                            checked={subTask.completed}
                            onChange={(e) => handleSubTaskToggle(task.id, index, e.target.checked)}
                          />
                          <Text 
                            style={{ 
                              marginLeft: 10, 
                              fontSize: 14,
                              textDecoration: subTask.completed ? 'line-through' : 'none',
                              color: subTask.completed ? '#999' : 'inherit'
                            }}
                          >
                            {subTask.text}
                          </Text>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {task.schedule && (
                  <div style={{ marginTop: 20, padding: '12px 16px', borderLeft: '3px solid #dbeafe', background: '#f8fbff', borderRadius: '0 8px 8px 0' }}>
                    <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>AI 建议日程</Text>
                    <Text style={{ fontSize: 14 }}>{task.schedule}</Text>
                  </div>
                )}

                <Divider style={{ margin: '20px 0' }} />

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space size="large">
                    <Select
                      value={task.status}
                      onChange={(value) => handleStatusChange(task.id, value as TaskStatus)}
                      style={{ width: 110 }}
                    >
                      <Option value="待执行">待执行</Option>
                      <Option value="进行中">进行中</Option>
                      <Option value="已完成">已完成</Option>
                    </Select>
                    {task.tags && task.tags.length > 0 && (
                      <Space wrap>
                        {task.tags.map((tag) => (
                          <Tag key={tag} color="blue" style={{ borderRadius: 6 }}>
                            #{tag}
                          </Tag>
                        ))}
                      </Space>
                    )}
                  </Space>
                  
                  <Space>
                    <Button 
                      type="text" 
                      icon={<EditOutlined />} 
                      onClick={() => handleEdit(task)}
                      style={{ color: '#5b7cff' }}
                    >
                      编辑
                    </Button>
                    <Popconfirm
                      title="确定删除任务？"
                      description="删除后将无法找回此任务及其子任务。"
                      onConfirm={() => handleDelete(task.id)}
                      okText="确定"
                      cancelText="取消"
                      okButtonProps={{ danger: true }}
                    >
                      <Button type="text" danger icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>
                  </Space>
                </div>
              </Card>
            </List.Item>
          )}
          locale={{ emptyText: <div className="empty-state">暂无匹配任务，换个筛选条件试试。</div> }}
        />
      </Card>

      <TaskEditModal
        open={editModalOpen}
        task={editingTask}
        onClose={handleCloseEditModal}
      />

      {/* 保存/编辑筛选预设 Modal */}
      <Modal
        title={editingPreset ? "编辑筛选预设" : "保存筛选预设"}
        open={presetModalVisible}
        onCancel={() => {
          setPresetModalVisible(false)
          setEditingPreset(null)
          presetForm.resetFields()
        }}
        onOk={handleSavePreset}
        okText="保存"
        cancelText="取消"
      >
        <Form form={presetForm} layout="vertical">
          <Form.Item
            name="name"
            label="预设名称"
            rules={[{ required: true, message: '请输入预设名称' }]}
          >
            <Input
              placeholder="例如：紧急任务、本周工作"
            />
          </Form.Item>
          <Form.Item label="当前筛选条件">
            <div style={{ fontSize: '14px', color: '#666' }}>
              {filterStatus && <div>状态: {filterStatus}</div>}
              {filterPriority && <div>优先级: {filterPriority}</div>}
              {filterCategory && <div>分类: {filterCategory}</div>}
              {filterTag && <div>标签: {filterTag}</div>}
              {searchKeyword && <div>关键词: {searchKeyword}</div>}
              {dateRange && <div>日期范围: {dateRange[0]} 至 {dateRange[1]}</div>}
              {progressRange && (progressRange[0] !== 0 || progressRange[1] !== 100) && <div>进度范围: {progressRange[0]}% - {progressRange[1]}%</div>}
              {!filterStatus && !filterPriority && !filterCategory && !filterTag && !searchKeyword && !dateRange && (progressRange[0] === 0 && progressRange[1] === 100) && (
                <div>无筛选条件</div>
              )}
            </div>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default TaskList
