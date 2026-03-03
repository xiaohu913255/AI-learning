import { Message, MessageContent } from '@/types/types'
import { Markdown } from '../Markdown'
import MessageImage from './Image'

type MessageRegularProps = {
  message: Message
  content: MessageContent | string
}

const MessageRegular: React.FC<MessageRegularProps> = ({
  message,
  content,
}) => {
  const isStrContent = typeof content === 'string'
  const isText = isStrContent || (!isStrContent && content.type == 'text')
  const isImage = !isStrContent && content.type === 'image_url'
  const isAudio = !isStrContent && content.type === 'audio_url'

  const markdownText = isStrContent ? content : (content.type === 'text' ? content.text : '')

  if (isImage) return <MessageImage content={content} />
  if (isAudio) return <audio controls src={content.audio_url.url} className="my-2" />

  return (
    <div
      className={`${
        message.role === 'user'
          ? 'bg-primary text-primary-foreground rounded-xl rounded-br-md px-4 py-3 text-left ml-auto mb-4'
          : 'text-gray-800 dark:text-gray-200 text-left items-start'
      } flex flex-col`}
    >
      <Markdown>{markdownText}</Markdown>
    </div>
  )
}

export default MessageRegular
