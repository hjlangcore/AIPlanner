import React, { useEffect, useState } from 'react'
import { Card, Button, Modal, Form, Input, Select, Typography, message, Popconfirm, Space, List, Tag, Checkbox } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { API_URL } from '../api/taskApi'
import { useAuthStore } from '../store/authStore'

const { Title, Text } = Typography
const { TextArea } = Input

interface TaskTemplate {
  id: number
  name: string
  description: string
  priority: string
  category: string
  tags: string[]
  sub_tasks: {
    text: string
    completed: boolean
  }[]
  notes: string
  created_at: string
}

const TaskTemplateManagement: React.FC = () => {
  const { isAuthenticated } = useAuthStore()
  const [templates, setTemplates] = useState<TaskTemplate[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<TaskTemplate | null>(null)
  const [form] = Form.useForm()
  const [subTasks, setSubTasks] = useState<{text: string, completed: boolean}[]>([])
  const [newSubTask, setNewSubTask] = useState('')

  useEffect(() => {
    if (isAuthenticated) {
      fetchTemplates()
    }
  }, [isAuthenticated])

  const fetchTemplates = async () => {
    try {
      const token = localStorage.getItem('token')
      if (!token) return
      
      const response = await fetch(`${API_URL}/task-templates`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      const data = await response.json()
      setTemplates(data)
    } catch (error) {
      console.error('获取模板失败', error)
      message.error('获取模板失败')
    }
  }

  const handleOpenModal = (template?: TaskTemplate) => {
    if (template) {
      setEditingTemplate(template)
      form.setFieldsValue({
        name: template.name,
        description: template.description,
        priority: template.priority,
        category: template.category,
        tags: template.tags.join(','),
        notes: template.notes
      })
      setSubTasks(template.sub_tasks)
    } else {
      setEditingTemplate(null)
      form.resetFields()
      setSubTasks([])
    }
    setModalOpen(true)
  }

  const handleCloseModal = () => {
    setModalOpen(false)
    setEditingTemplate(null)
    setSubTasks([])
    setNewSubTask('')
  }

  const handleAddSubTask = () => {
    if (newSubTask.trim()) {
      setSubTasks([...subTasks, { text: newSubTask.trim(), completed: false }])
      setNewSubTask('')
    }
  }

  const handleRemoveSubTask = (index: number) => {
    setSubTasks(subTasks.filter((_, i) => i !== index))
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      const token = localStorage.getItem('token')
      if (!token) {
        message.error('请先登录')
        return
      }

      const templateData = {
        name: values.name,
        description: values.description,
        priority: values.priority,
        category: values.category,
        tags: values.tags ? values.tags.split(',').map((tag: string) => tag.trim()) : [],
        sub_tasks: subTasks,
        notes: values.notes
      }

      let response
      if (editingTemplate) {
        response = await fetch(`${API_URL}/task-templates/${editingTemplate.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(templateData)
        })
      } else {
        response = await fetch(`${API_URL}/task-templates`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(templateData)
        })
      }

      const data = await response.json()
      if (data.success) {
        message.success(editingTemplate ? '模板更新成功' : '模板创建成功')
        handleCloseModal()
        fetchTemplates()
      } else {
        message.error(data.detail || '保存失败')
      }
    } catch (error) {
      console.error('保存模板失败', error)
      message.error('保存模板失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      const token = localStorage.getItem('token')
      if (!token) return

      const response = await fetch(`${API_URL}/task-templates/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      const data = await response.json()
      if (data.success) {
        message.success('模板删除成功')
        fetchTemplates()
      } else {
        message.error(data.detail || '删除失败')
      }
    } catch (error) {
      console.error('删除模板失败', error)
      message.error('删除模板失败')
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="page-section">
        <Card>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Text type="secondary">请先登录以管理任务模板</Text>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="page-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>任务模板管理</Title>
          <Text type="secondary">创建和管理常用任务模板，提高创建效率</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
          添加模板
        </Button>
      </div>

      <List
        grid={{ gutter: 16, column: 4 }}
        dataSource={templates}
        renderItem={(template) => (
          <List.Item>
            <Card
              hoverable
              title={template.name}
              extra={
                <Space size="small">
                  <Button 
                    type="text" 
                    icon={<EditOutlined />} 
                    onClick={() => handleOpenModal(template)}
                  />
                  <Popconfirm
                    title="确定删除此模板？"
                    onConfirm={() => handleDelete(template.id)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button type="text" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              }
            >
              {template.description && (
                <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
                  {template.description}
                </Text>
              )}
              <Space size="small" style={{ marginBottom: 8, display: 'block' }}>
                <Tag color="blue">{template.priority}</Tag>
                <Tag color="green">{template.category}</Tag>
              </Space>
              {template.tags.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <Text style={{ fontSize: 12, color: '#999' }}>标签:</Text>
                  <Space size="small" wrap>
                    {template.tags.map((tag, index) => (
                      <Tag key={index}>{tag}</Tag>
                    ))}
                  </Space>
                </div>
              )}
              {template.sub_tasks.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <Text style={{ fontSize: 12, color: '#999' }}>子任务 ({template.sub_tasks.length}项):</Text>
                  <ul style={{ margin: '8px 0 0 16px', padding: 0 }}>
                    {template.sub_tasks.slice(0, 3).map((subTask, index) => (
                      <li key={index} style={{ fontSize: 12, marginBottom: 2 }}>
                        {subTask.text}
                      </li>
                    ))}
                    {template.sub_tasks.length > 3 && (
                      <li style={{ fontSize: 12, color: '#999' }}>
                        ... 还有 {template.sub_tasks.length - 3} 项
                      </li>
                    )}
                  </ul>
                </div>
              )}
              <Text type="secondary" style={{ fontSize: 12 }}>
                创建于: {new Date(template.created_at).toLocaleString()}
              </Text>
            </Card>
          </List.Item>
        )}
        locale={{ emptyText: <div className="empty-state">暂无任务模板，点击"添加模板"开始创建</div> }}
      />

      <Modal
        title={editingTemplate ? '编辑任务模板' : '添加任务模板'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={handleCloseModal}
        okText="保存"
        cancelText="取消"
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="例如：周会准备、项目启动" />
          </Form.Item>

          <Form.Item name="description" label="模板描述">
            <TextArea rows={3} placeholder="模板的详细描述" />
          </Form.Item>

          <Form.Item
            name="priority"
            label="优先级"
            initialValue="中"
          >
            <Select>
              <Select.Option value="高">高</Select.Option>
              <Select.Option value="中">中</Select.Option>
              <Select.Option value="低">低</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="category"
            label="分类"
            initialValue="默认"
          >
            <Select>
              <Select.Option value="工作">工作</Select.Option>
              <Select.Option value="学习">学习</Select.Option>
              <Select.Option value="生活">生活</Select.Option>
              <Select.Option value="健康">健康</Select.Option>
              <Select.Option value="默认">默认</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="tags" label="标签 (逗号分隔)">
            <Input placeholder="例如：重要,紧急,会议" />
          </Form.Item>

          <Form.Item label="子任务">
            <div style={{ marginBottom: 8 }}>
              <Space style={{ width: '100%' }}>
                <Input
                  value={newSubTask}
                  onChange={(e) => setNewSubTask(e.target.value)}
                  placeholder="输入子任务"
                  onKeyPress={(e) => e.key === 'Enter' && handleAddSubTask()}
                />
                <Button type="primary" onClick={handleAddSubTask}>
                  添加
                </Button>
              </Space>
            </div>
            <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: 4, padding: 8 }}>
              {subTasks.map((subTask, index) => (
                <div key={index} style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                  <Checkbox checked={subTask.completed} onChange={(e) => {
                    const newSubTasks = [...subTasks]
                    newSubTasks[index].completed = e.target.checked
                    setSubTasks(newSubTasks)
                  }} />
                  <Input
                    value={subTask.text}
                    onChange={(e) => {
                      const newSubTasks = [...subTasks]
                      newSubTasks[index].text = e.target.value
                      setSubTasks(newSubTasks)
                    }}
                    style={{ marginLeft: 8, flex: 1 }}
                  />
                  <Button type="text" danger onClick={() => handleRemoveSubTask(index)}>
                    删除
                  </Button>
                </div>
              ))}
              {subTasks.length === 0 && (
                <Text type="secondary">暂无子任务</Text>
              )}
            </div>
          </Form.Item>

          <Form.Item name="notes" label="备注">
            <TextArea rows={2} placeholder="模板备注信息" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default TaskTemplateManagement