import React, { useState, useEffect } from 'react'
import { Modal, Form, Input, Select, DatePicker, Tag, Button, Space, Divider, InputNumber, message } from 'antd'
import { PlusOutlined, MinusCircleOutlined } from '@ant-design/icons'
import { useTaskStore } from '../store/taskStore'
import { Task, SubTask } from '../types/task'
import dayjs from 'dayjs'

const { TextArea } = Input
const { Option } = Select

interface TaskEditModalProps {
  open: boolean
  task: Task | null
  onClose: () => void
}

const TaskEditModal: React.FC<TaskEditModalProps> = ({ open, task, onClose }) => {
  const [form] = Form.useForm()
  const { updateTask, updateTaskProgress } = useTaskStore()
  const [subTasks, setSubTasks] = useState<SubTask[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [newTag, setNewTag] = useState('')

  useEffect(() => {
    if (task && open) {
      form.setFieldsValue({
        raw_task: task.raw_task,
        priority: task.priority,
        status: task.status,
        deadline: task.deadline ? dayjs(task.deadline) : null,
        category: task.category,
        notes: task.notes,
        progress: task.progress,
        schedule: task.schedule,
      })
      setSubTasks(task.sub_tasks || [])
      setTags(task.tags || [])
    }
  }, [task, open, form])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      if (!task) return

      const updateData: Partial<Task> = {
        raw_task: values.raw_task,
        priority: values.priority,
        status: values.status,
        deadline: values.deadline ? values.deadline.format('YYYY-MM-DD') : null,
        category: values.category,
        notes: values.notes,
        sub_tasks: subTasks,
        tags: tags,
        schedule: values.schedule,
      }

      await updateTask(task.id, updateData)
      
      if (values.progress !== undefined && values.progress !== task.progress) {
        await updateTaskProgress(task.id, values.progress)
      }

      message.success('任务更新成功')
      onClose()
    } catch (error) {
      console.error('更新任务失败:', error)
    }
  }

  const handleAddSubTask = () => {
    setSubTasks([...subTasks, { text: '', completed: false }])
  }

  const handleRemoveSubTask = (index: number) => {
    setSubTasks(subTasks.filter((_, i) => i !== index))
  }

  const handleSubTaskChange = (index: number, value: string) => {
    const newSubTasks = [...subTasks]
    newSubTasks[index] = { ...newSubTasks[index], text: value }
    setSubTasks(newSubTasks)
  }

  const handleAddTag = () => {
    if (newTag && !tags.includes(newTag)) {
      setTags([...tags, newTag])
      setNewTag('')
    }
  }

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove))
  }

  return (
    <Modal
      title="编辑任务"
      open={open}
      onOk={handleOk}
      onCancel={onClose}
      width={700}
      okText="保存"
      cancelText="取消"
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          priority: '中',
          status: '待执行',
          progress: 0,
        }}
      >
        <Form.Item
          name="raw_task"
          label="任务名称"
          rules={[{ required: true, message: '请输入任务名称' }]}
        >
          <Input placeholder="请输入任务名称" />
        </Form.Item>

        <Form.Item name="notes" label="备注">
          <TextArea rows={3} placeholder="添加备注信息（可选）" />
        </Form.Item>

        <Divider orientation="left">任务属性</Divider>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <Form.Item name="priority" label="优先级">
            <Select>
              <Option value="高">高</Option>
              <Option value="中">中</Option>
              <Option value="低">低</Option>
            </Select>
          </Form.Item>

          <Form.Item name="status" label="状态">
            <Select>
              <Option value="待执行">待执行</Option>
              <Option value="进行中">进行中</Option>
              <Option value="已完成">已完成</Option>
              <Option value="已过期">已过期</Option>
            </Select>
          </Form.Item>

          <Form.Item name="deadline" label="截止日期">
            <DatePicker style={{ width: '100%' }} placeholder="选择截止日期" />
          </Form.Item>

          <Form.Item name="category" label="分类">
            <Input placeholder="输入分类名称" />
          </Form.Item>

          <Form.Item name="progress" label="完成进度 (%)">
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
        </div>

        <Form.Item name="schedule" label="日程安排">
          <TextArea rows={2} placeholder="AI 建议的日程安排（可选）" />
        </Form.Item>

        <Divider orientation="left">子任务</Divider>

        <div style={{ marginBottom: 16 }}>
          {subTasks.map((subTask, index) => (
            <Space key={index} style={{ display: 'flex', marginBottom: 8, width: '100%' }}>
              <Input
                value={subTask.text}
                onChange={(e) => handleSubTaskChange(index, e.target.value)}
                placeholder={`子任务 ${index + 1}`}
                style={{ flex: 1 }}
              />
              <Button
                type="text"
                danger
                icon={<MinusCircleOutlined />}
                onClick={() => handleRemoveSubTask(index)}
              />
            </Space>
          ))}
          <Button type="dashed" onClick={handleAddSubTask} icon={<PlusOutlined />} block>
            添加子任务
          </Button>
        </div>

        <Divider orientation="left">标签</Divider>

        <div style={{ marginBottom: 16 }}>
          <Space wrap style={{ marginBottom: 8 }}>
            {tags.map(tag => (
              <Tag
                key={tag}
                closable
                onClose={() => handleRemoveTag(tag)}
                color="blue"
              >
                #{tag}
              </Tag>
            ))}
          </Space>
          <Space>
            <Input
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onPressEnter={handleAddTag}
              placeholder="输入标签后按回车"
              style={{ width: 150 }}
            />
            <Button type="primary" size="small" onClick={handleAddTag}>
              添加
            </Button>
          </Space>
        </div>
      </Form>
    </Modal>
  )
}

export default TaskEditModal
