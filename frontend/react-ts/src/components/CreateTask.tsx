import React, { useState, useEffect } from 'react'
import { Card, Input, Button, Spin, Typography, Steps, Progress, Space, Tag, Modal, List, Alert, Form, DatePicker, Select, Segmented, Divider, Row, Col } from 'antd'
import { LoadingOutlined, CheckCircleOutlined, SaveOutlined, WarningOutlined, PlusOutlined, MinusCircleOutlined, RobotOutlined, EditOutlined } from '@ant-design/icons'
import { useTaskStore } from '../store/taskStore'
import { useAuthStore } from '../store/authStore'
import { toast } from 'react-toastify'
import { taskApi } from '../api/taskApi'
import { TaskTemplate, TaskPriority } from '../types/task'

const { TextArea } = Input
const { Title, Text } = Typography
const { Step } = Steps

const CreateTask: React.FC = () => {
  const { createTask, loading } = useTaskStore()
  const { isAuthenticated } = useAuthStore()
  const [input, setInput] = useState('')
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState(0)
  const [result, setResult] = useState<any>(null)
  const [templates, setTemplates] = useState<TaskTemplate[]>([])
  const [templateModalVisible, setTemplateModalVisible] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<TaskTemplate | null>(null)
  const [customDeadline, setCustomDeadline] = useState<string>()
  const [conflicts, setConflicts] = useState<any[]>([])
  const [conflictCheckLoading, setConflictCheckLoading] = useState(false)
  const [templateForm] = Form.useForm()
  const [manualForm] = Form.useForm()

  // 创建模式：ai = AI智能创建, manual = 手动创建
  const [createMode, setCreateMode] = useState<'ai' | 'manual'>('ai')

  // 手动创建表单状态
  const [manualSubTasks, setManualSubTasks] = useState<string[]>([])
  const [manualSubTaskInput, setManualSubTaskInput] = useState('')

  // 用于存储setTimeout的timer ID，便于组件卸载时清理
  const [resetTimer] = useState<{ current: any }>({ current: null })

  const steps = [
    { title: '输入任务', description: '用自然语言描述你的任务' },
    { title: 'AI分析', description: 'AI正在分析和拆解任务' },
    { title: '任务生成', description: '生成任务和子任务' },
    { title: '冲突检测', description: '检查任务时间冲突' },
    { title: '完成', description: '任务创建成功' }
  ]

  useEffect(() => {
    if (isAuthenticated) {
      fetchTemplates()
    }
  }, [isAuthenticated])

  const fetchTemplates = async () => {
    try {
      const response = await taskApi.getTaskTemplates()
      setTemplates(response.data || [])
    } catch (error) {
      console.error('获取模板失败', error)
    }
  }

  // 组件卸载时清理timer，防止内存泄漏
  useEffect(() => {
    return () => {
      if (resetTimer.current) {
        clearTimeout(resetTimer.current)
      }
    }
  }, [])

  const checkTaskConflicts = async (deadline: string) => {
    try {
      setConflictCheckLoading(true)
      const response = await taskApi.checkTaskConflicts(deadline)
      setConflicts(response.data || [])
      return response.data || []
    } catch (error) {
      console.error('检查任务冲突失败:', error)
      setConflicts([])
      return []
    } finally {
      setConflictCheckLoading(false)
    }
  }

  // 输入验证函数
  const validateInput = (text: string): { valid: boolean; message?: string } => {
    const trimmed = text.trim()
    
    // 检查是否为空
    if (!trimmed) {
      return { valid: false, message: '请输入任务描述' }
    }
    
    // 检查最小长度
    if (trimmed.length < 2) {
      return { valid: false, message: '任务描述至少需要2个字符' }
    }
    
    // 检查最大长度 (防止数据库溢出和LLM处理超时)
    if (trimmed.length > 2000) {
      return { valid: false, message: '任务描述不能超过2000个字符' }
    }
    
    // 检查危险字符模式
    const dangerousPatterns = [
      /<script/i,
      /javascript:/i,
      /on\w+=/i,  // 事件处理器如 onclick=
      /<iframe/i,
      /<object/i,
      /<embed/i,
    ]
    
    for (const pattern of dangerousPatterns) {
      if (pattern.test(trimmed)) {
        return { valid: false, message: '输入包含不支持的特殊字符，请重新输入' }
      }
    }
    
    return { valid: true }
  }

  const handleSubmit = async () => {
    // 执行输入验证
    const validation = validateInput(input)
    if (!validation.valid) {
      toast.error(validation.message)
      return
    }

    setCurrentStep(1)
    setProgress(25)

    try {
      console.log('开始处理任务创建:', input)
      
      // 模拟处理过程
      setTimeout(() => {
        setProgress(50)
        setCurrentStep(2)
      }, 1000)

      setTimeout(() => {
        setProgress(75)
      }, 2000)

      const res = await createTask(input)
      console.log('任务创建结果:', res)
      
      if (res.success) {
        setResult(res)
        setProgress(85)
        setCurrentStep(3)
        
        // 检查任务冲突
        if (res.task_info && res.task_info.deadline) {
          await checkTaskConflicts(res.task_info.deadline)
        }
        
        setProgress(100)
        setCurrentStep(4)
        toast.success('任务创建成功！')

        // 重置表单 - 先清除已存在的timer防止多次触发
        if (resetTimer.current) {
          clearTimeout(resetTimer.current)
        }
        resetTimer.current = setTimeout(() => {
          setInput('')
          setProgress(0)
          setCurrentStep(0)
          setResult(null)
          setConflicts([])
        }, 3000)
      } else {
        throw new Error(res.error || '创建任务失败')
      }
    } catch (error) {
      console.error('任务创建失败:', error)
      toast.error('任务创建失败，请重试')
      setProgress(0)
      setCurrentStep(0)
      setConflicts([])
    }
  }

  const handleManualSubmit = async () => {
    try {
      const values = await manualForm.validateFields()
      
      setCurrentStep(1)
      setProgress(30)
      
      const res = await taskApi.createTaskManual({
        raw_task: values.taskName + (values.description ? ` - ${values.description}` : ''),
        deadline: values.deadline ? values.deadline.format('YYYY-MM-DD') : null,
        priority: values.priority || '中',
        category: values.category || '默认',
        sub_tasks: manualSubTasks.length > 0 ? manualSubTasks : undefined,
        notes: values.notes || ''
      })
      
      setProgress(70)
      
      if (res.data.success) {
        setResult({
          success: true,
          task_info: {
            task_name: values.taskName,
            deadline: values.deadline || null,
            priority: values.priority || '中',
            sub_tasks: manualSubTasks
          }
        })
        setProgress(85)
        setCurrentStep(3)
        
        // 检查任务冲突
        if (values.deadline) {
          await checkTaskConflicts(values.deadline)
        }
        
        setProgress(100)
        setCurrentStep(4)
        toast.success('任务创建成功！')
        
        // 重置表单
        if (resetTimer.current) {
          clearTimeout(resetTimer.current)
        }
        resetTimer.current = setTimeout(() => {
          manualForm.resetFields()
          setManualSubTasks([])
          setManualSubTaskInput('')
          setProgress(0)
          setCurrentStep(0)
          setResult(null)
          setConflicts([])
        }, 3000)
      } else {
        throw new Error(res.data.error || '创建任务失败')
      }
    } catch (error: any) {
      console.error('手动创建任务失败:', error)
      if (error.errorFields) {
        toast.error('请完善表单信息')
      } else {
        toast.error('任务创建失败，请重试')
      }
      setProgress(0)
      setCurrentStep(0)
    }
  }

  const addManualSubTask = () => {
    const text = manualSubTaskInput.trim()
    if (!text) return
    if (manualSubTasks.includes(text)) {
      toast.info('该子任务已存在')
      return
    }
    setManualSubTasks([...manualSubTasks, text])
    setManualSubTaskInput('')
  }

  const removeManualSubTask = (index: number) => {
    setManualSubTasks(manualSubTasks.filter((_, i) => i !== index))
  }

  const handleSelectTemplate = (template: TaskTemplate) => {
    setSelectedTemplate(template)
    templateForm.resetFields()
    templateForm.setFieldsValue({
      name: template.name,
      description: template.description,
    })
  }

  const handleUseTemplate = async () => {
    if (!selectedTemplate) {
      toast.error('请先选择一个模板')
      return
    }

    try {
      // 构建完整的任务描述，包含模板的所有信息
      let taskDescription = selectedTemplate.name
      if (selectedTemplate.description) {
        taskDescription += ` - ${selectedTemplate.description}`
      }

      // 添加子任务信息
      if (selectedTemplate.sub_tasks && selectedTemplate.sub_tasks.length > 0) {
        const subTaskTexts = selectedTemplate.sub_tasks.map(st => typeof st === 'string' ? st : st.text).filter(Boolean)
        if (subTaskTexts.length > 0) {
          taskDescription += `，包含子任务：${subTaskTexts.join('、')}`
        }
      }

      // 添加分类和优先级信息
      taskDescription += ` (分类：${selectedTemplate.category}，优先级：${selectedTemplate.priority})`

      // 如果有自定义截止日期，也加上
      if (customDeadline) {
        taskDescription += `，截止日期：${customDeadline}`
      }

      // 添加标签信息
      if (selectedTemplate.tags && selectedTemplate.tags.length > 0) {
        taskDescription += `，标签：${selectedTemplate.tags.join('、')}`
      }

      if (selectedTemplate.notes) {
        taskDescription += `，备注：${selectedTemplate.notes}`
      }

      setInput(taskDescription)
      setTemplateModalVisible(false)
      setSelectedTemplate(null)
      toast.success('已应用模板信息')
    } catch (error) {
      console.error('使用模板失败', error)
      toast.error('使用模板失败')
    }
  }

  return (
    <div className="page-section">
      <div className="page-hero">
        <Text className="page-hero-kicker">Create With AI</Text>
        <Title level={3} className="page-hero-title">
          用一句自然语言，快速生成结构化任务
        </Title>
        <Text className="page-hero-description">
          你只需要描述目标、时间或场景，系统会自动拆解任务、补全信息并生成更容易执行的计划。
        </Text>
      </div>

      <div className="create-panel">
        <Card className="glass-card">
          <Steps current={currentStep} style={{ marginBottom: 28 }}>
            {steps.map((step, index) => (
              <Step key={index} title={step.title} description={step.description} />
            ))}
          </Steps>

          {currentStep === 0 && (
            <Space direction="vertical" size={18} style={{ width: '100%' }}>
              {/* 创建模式切换 */}
              <div style={{ textAlign: 'center', marginBottom: 8 }}>
                <Segmented
                  value={createMode}
                  onChange={(val) => {
                    setCreateMode(val as 'ai' | 'manual')
                    setCurrentStep(0)
                    setProgress(0)
                    setResult(null)
                  }}
                  options={[
                    {
                      label: (
                        <span style={{ padding: '0 8px' }}>
                          <RobotOutlined style={{ marginRight: 6 }} />
                          AI 智能创建
                        </span>
                      ),
                      value: 'ai'
                    },
                    {
                      label: (
                        <span style={{ padding: '0 8px' }}>
                          <EditOutlined style={{ marginRight: 6 }} />
                          手动创建
                        </span>
                      ),
                      value: 'manual'
                    }
                  ]}
                />
              </div>

              {createMode === 'ai' ? (
                <>
                  <div>
                    <Title level={4} className="section-title">
                      输入任务描述
                    </Title>
                    <Text className="section-subtitle">
                      尽量描述清楚时间、对象和目标，AI 会更容易拆解出高质量任务。
                    </Text>
                  </div>
                  <TextArea
                    rows={6}
                    placeholder="例如：下周五前完成项目报告，并安排两次团队同步会议；或者：明天下午 3 点和产品讨论迭代计划"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                  />
                  <Space wrap>
                    <Tag color="blue">支持自然语言</Tag>
                    <Tag color="purple">自动识别时间</Tag>
                    <Tag color="green">可拆分子任务</Tag>
                  </Space>
                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                    {isAuthenticated && (
                      <Button
                        icon={<SaveOutlined />}
                        onClick={() => setTemplateModalVisible(true)}
                      >
                        从模板创建
                      </Button>
                    )}
                    <Button
                      type="primary"
                      size="large"
                      onClick={handleSubmit}
                      loading={loading}
                      disabled={!input.trim()}
                    >
                      生成智能任务
                    </Button>
                  </Space>
                </>
              ) : (
                <>
                  <div>
                    <Title level={4} className="section-title">
                      手动填写任务信息
                    </Title>
                    <Text className="section-subtitle">
                      精确控制任务的每个字段，适合需要自定义细节的场景。
                    </Text>
                  </div>
                  <Form form={manualForm} layout="vertical" style={{ width: '100%' }}>
                    <Row gutter={16}>
                      <Col span={16}>
                        <Form.Item
                          name="taskName"
                          label="任务名称"
                          rules={[{ required: true, message: '请输入任务名称' }]}
                        >
                          <Input placeholder="例如：完成项目报告" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item
                          name="priority"
                          label="优先级"
                          initialValue="中"
                        >
                          <Select
                            options={[
                              { label: '高', value: '高' },
                              { label: '中', value: '中' },
                              { label: '低', value: '低' }
                            ]}
                          />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="deadline" label="截止日期">
                          <DatePicker
                            style={{ width: '100%' }}
                            placeholder="选择截止日期"
                            format="YYYY-MM-DD"
                          />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name="category"
                          label="分类"
                          initialValue="默认"
                        >
                          <Select
                            options={[
                              { label: '工作', value: '工作' },
                              { label: '学习', value: '学习' },
                              { label: '生活', value: '生活' },
                              { label: '健康', value: '健康' },
                              { label: '默认', value: '默认' }
                            ]}
                          />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Form.Item name="description" label="任务描述">
                      <TextArea
                        rows={2}
                        placeholder="补充描述任务的详细信息（可选）"
                      />
                    </Form.Item>

                    <Form.Item label="子任务">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space.Compact style={{ width: '100%' }}>
                          <Input
                            placeholder="输入子任务后按回车或点击添加"
                            value={manualSubTaskInput}
                            onChange={(e) => setManualSubTaskInput(e.target.value)}
                            onPressEnter={addManualSubTask}
                          />
                          <Button icon={<PlusOutlined />} onClick={addManualSubTask}>
                            添加
                          </Button>
                        </Space.Compact>
                        {manualSubTasks.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                            {manualSubTasks.map((task, index) => (
                              <Tag
                                key={index}
                                closable
                                onClose={() => removeManualSubTask(index)}
                                style={{ padding: '4px 8px' }}
                              >
                                {task}
                              </Tag>
                            ))}
                          </div>
                        )}
                      </Space>
                    </Form.Item>

                    <Form.Item name="notes" label="备注">
                      <TextArea
                        rows={2}
                        placeholder="添加备注信息（可选）"
                      />
                    </Form.Item>

                    <div style={{ textAlign: 'right' }}>
                      <Button
                        type="primary"
                        size="large"
                        onClick={handleManualSubmit}
                        loading={loading}
                      >
                        创建任务
                      </Button>
                    </div>
                  </Form>
                </>
              )}
            </Space>
          )}

          {currentStep > 0 && currentStep < 4 && (
            <div style={{ textAlign: 'center', padding: '52px 0' }}>
              <Spin indicator={<LoadingOutlined style={{ fontSize: 52 }} spin />} />
              <Progress
                percent={progress}
                strokeColor={{ '0%': '#5b7cff', '100%': '#39bdf8' }}
                status="active"
                style={{ marginTop: 28, width: '82%', marginInline: 'auto' }}
              />
              <Text style={{ display: 'block', marginTop: 16 }}>
                {currentStep === 1 ? 'AI 正在分析任务语义和时间信息...' : 
                 currentStep === 2 ? '正在生成主任务与可执行子任务...' : 
                 '正在检查任务时间冲突...'}
              </Text>
            </div>
          )}

          {currentStep === 4 && result && (
            <div className="result-panel">
              <div style={{ textAlign: 'center', marginBottom: 20 }}>
                <CheckCircleOutlined style={{ fontSize: 52, color: '#22c55e' }} />
                <Text style={{ display: 'block', marginTop: 16, fontSize: 20, fontWeight: 700 }}>
                  任务创建成功
                </Text>
              </div>
              {result.task_info && (
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <Title level={5}>任务信息</Title>
                  <Text><strong>任务名称:</strong> {result.task_info.task_name}</Text>
                  <Text><strong>截止日期:</strong> {result.task_info.deadline}</Text>
                  <Text><strong>优先级:</strong> {result.task_info.priority}</Text>
                  {result.task_info.sub_tasks && result.task_info.sub_tasks.length > 0 && (
                    <>
                      <Title level={5} style={{ marginTop: 8 }}>子任务</Title>
                      <ul style={{ paddingLeft: 18, marginBottom: 0 }}>
                        {result.task_info.sub_tasks.map((subTask: string, index: number) => (
                          <li key={index} style={{ marginBottom: 6 }}>{subTask}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  
                  {/* 任务冲突检测结果 */}
                  {conflicts.length > 0 && (
                    <>
                      <Title level={5} style={{ marginTop: 16 }}>任务冲突检测</Title>
                      <Alert
                        message="检测到任务冲突"
                        description={
                          <div>
                            <Text type="warning">在该截止日期已有其他任务，请合理安排时间。</Text>
                            <List
                              size="small"
                              dataSource={conflicts.slice(0, 3)} // 只显示前3个冲突任务
                              renderItem={(item) => (
                                <List.Item>
                                  <List.Item.Meta
                                    title={item.raw_task}
                                    description={
                                      <Space direction="vertical" size={4}>
                                        <Text type="secondary">截止日期: {item.deadline}</Text>
                                        <Text type="secondary">优先级: {item.priority}</Text>
                                      </Space>
                                    }
                                  />
                                </List.Item>
                              )}
                            />
                            {conflicts.length > 3 && (
                              <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                                还有 {conflicts.length - 3} 个冲突任务未显示
                              </Text>
                            )}
                          </div>
                        }
                        type="warning"
                        showIcon
                      />
                    </>
                  )}
                  
                  {conflicts.length === 0 && (
                    <>
                      <Title level={5} style={{ marginTop: 16 }}>任务冲突检测</Title>
                      <Alert
                        message="未检测到任务冲突"
                        description="该截止日期没有其他任务，可以放心安排。"
                        type="success"
                        showIcon
                      />
                    </>
                  )}
                </Space>
              )}
            </div>
          )}
        </Card>

        <Card className="surface-card">
          <Space direction="vertical" size={18} style={{ width: '100%' }}>
            <div>
              <Text className="page-kicker">输入建议</Text>
              <Title level={4} className="section-title">
                这样描述会更好用
              </Title>
            </div>
            <div className="tip-list">
              <div className="tip-item">
                <Text strong>带上时间</Text>
                <br />
                <Text type="secondary">例如“周五下班前”“明天下午 3 点”</Text>
              </div>
              <div className="tip-item">
                <Text strong>说明目标</Text>
                <br />
                <Text type="secondary">例如“完成报告”“准备会议材料”“整理客户反馈”</Text>
              </div>
              <div className="tip-item">
                <Text strong>包含上下文</Text>
                <br />
                <Text type="secondary">例如“和市场部沟通”“为产品评审准备”</Text>
              </div>
            </div>
          </Space>
        </Card>

        {/* 模板选择模态框 */}
        <Modal
          title="选择任务模板"
          open={templateModalVisible}
          onCancel={() => {
            setTemplateModalVisible(false)
            setSelectedTemplate(null)
            templateForm.resetFields()
          }}
          onOk={handleUseTemplate}
          okText="应用模板"
          okButtonProps={{ disabled: !selectedTemplate }}
          cancelText="取消"
          width={700}
        >
          {!selectedTemplate ? (
            <List
              dataSource={templates}
              renderItem={(template) => (
                <List.Item
                  actions={[
                    <Button 
                      key="select" 
                      type={selectedTemplate?.id === template.id ? "primary" : "default"}
                      size="small" 
                      onClick={() => handleSelectTemplate(template)}
                    >
                      选择此模板
                    </Button>
                  ]}
                  style={{
                    background: selectedTemplate?.id === template.id ? '#f0f7ff' : 'transparent',
                    borderRadius: '8px',
                    marginBottom: '8px'
                  }}
                >
                  <List.Item.Meta
                    title={template.name}
                    description={
                      <Space direction="vertical" size={4}>
                        {template.description && (
                          <Text type="secondary">{template.description}</Text>
                        )}
                        <Space size="small">
                          <Tag color={template.priority === '高' ? 'red' : template.priority === '中' ? 'orange' : 'green'}>
                            {template.priority}优先级
                          </Tag>
                          <Tag color="blue">{template.category}</Tag>
                          {template.tags && template.tags.length > 0 && (
                            template.tags.map(tag => (
                              <Tag key={tag} color="purple">#{tag}</Tag>
                            ))
                          )}
                        </Space>
                        {template.sub_tasks && template.sub_tasks.length > 0 && (
                          <div>
                            <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>
                              包含 {template.sub_tasks.length} 个子任务：
                            </Text>
                            <div style={{ marginLeft: 16 }}>
                              {template.sub_tasks.slice(0, 3).map((st, i) => {
                                const text = typeof st === 'string' ? st : st.text
                                return text ? <div key={i} style={{ fontSize: '13px', color: '#666' }}>• {text}</div> : null
                              })}
                              {template.sub_tasks.length > 3 && (
                                <Text type="secondary" style={{ fontSize: '12px' }}>
                                  还有 {template.sub_tasks.length - 3} 个子任务...
                                </Text>
                              )}
                            </div>
                          </div>
                        )}
                        {template.notes && (
                          <Text type="secondary" style={{ fontSize: '12px' }}>备注: {template.notes}</Text>
                        )}
                      </Space>
                    }
                  />
                </List.Item>
              )}
              locale={{ emptyText: <div className="empty-state">暂无任务模板，请先在模板管理中创建</div> }}
            />
          ) : (
            <div>
              <div style={{ marginBottom: 16 }}>
                <Text strong style={{ fontSize: 16 }}>{selectedTemplate.name}</Text>
                {selectedTemplate.description && (
                  <Text type="secondary" style={{ display: 'block', marginTop: 4 }}>{selectedTemplate.description}</Text>
                )}
              </div>

              <Form form={templateForm} layout="vertical">
                <Form.Item label="自定义截止日期（可选）">
                  <DatePicker
                    showTime
                    style={{ width: '100%' }}
                    placeholder="选择截止日期"
                    onChange={(date, dateString) => setCustomDeadline(dateString || '')}
                  />
                </Form.Item>

                <div style={{ marginTop: 24, padding: 16, background: '#fafafa', borderRadius: 8 }}>
                  <Title level={5} style={{ marginBottom: 12 }}>模板信息预览</Title>
                  <Space direction="vertical" size={8} style={{ width: '100%' }}>
                    <div>
                      <Text type="secondary" style={{ marginRight: 8 }}>优先级:</Text>
                      <Tag color={selectedTemplate.priority === '高' ? 'red' : selectedTemplate.priority === '中' ? 'orange' : 'green'}>
                        {selectedTemplate.priority}
                      </Tag>
                    </div>
                    <div>
                      <Text type="secondary" style={{ marginRight: 8 }}>分类:</Text>
                      <Tag color="blue">{selectedTemplate.category}</Tag>
                    </div>
                    {selectedTemplate.tags && selectedTemplate.tags.length > 0 && (
                      <div>
                        <Text type="secondary" style={{ marginRight: 8 }}>标签:</Text>
                        <Space size="small">
                          {selectedTemplate.tags.map(tag => (
                            <Tag key={tag} color="purple">#{tag}</Tag>
                          ))}
                        </Space>
                      </div>
                    )}
                    {selectedTemplate.sub_tasks && selectedTemplate.sub_tasks.length > 0 && (
                      <div>
                        <Text type="secondary" style={{ marginRight: 8, display: 'block', marginBottom: 4 }}>
                          子任务 ({selectedTemplate.sub_tasks.length}个):
                        </Text>
                        <ul style={{ margin: 0, paddingLeft: 20 }}>
                          {selectedTemplate.sub_tasks.map((st, i) => {
                            const text = typeof st === 'string' ? st : st.text
                            return text ? <li key={i} style={{ marginBottom: 4 }}>{text}</li> : null
                          })}
                        </ul>
                      </div>
                    )}
                    {selectedTemplate.notes && (
                      <div>
                        <Text type="secondary" style={{ marginRight: 8 }}>备注:</Text>
                        <Text>{selectedTemplate.notes}</Text>
                      </div>
                    )}
                  </Space>
                </div>

                <div style={{ marginTop: 16, textAlign: 'center' }}>
                  <Button onClick={() => setSelectedTemplate(null)}>重新选择模板</Button>
                </div>
              </Form>
            </div>
          )}
        </Modal>
      </div>
    </div>
  )
}

export default CreateTask
