import { cancelChat } from '@/api/chat'
import { uploadImage } from '@/api/upload'
import { Button } from '@/components/ui/button'
import { useConfigs } from '@/contexts/configs'
import { eventBus, TCanvasAddImagesToChatEvent } from '@/lib/event'
import { cn, dataURLToFile } from '@/lib/utils'
import { Message, Model } from '@/types/types'
import { useMutation } from '@tanstack/react-query'
import { useDrop } from 'ahooks'
import { produce } from 'immer'
import { AnimatePresence, motion } from 'motion/react'
import Textarea, { TextAreaRef } from 'rc-textarea'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import ModelSelector from './ModelSelector'
import { PlusIcon, XIcon, ArrowUp, Square, Loader2, Video, Image, Music } from 'lucide-react'
import { uploadVideo, uploadAudio } from '@/api/upload'

type ChatTextareaProps = {
  pending: boolean
  className?: string
  messages: Message[]
  sessionId?: string
  onSendMessages: (
    data: Message[],
    configs: {
      textModel: Model
      imageModel: Model
      videoModel?: Model
      autoModelSelection?: boolean
    }
  ) => void
  onCancelChat?: () => void
}

const ChatTextarea: React.FC<ChatTextareaProps> = ({
  pending,
  className,
  messages,
  sessionId,
  onSendMessages,
  onCancelChat,
}) => {
  const { t } = useTranslation()
  const { textModel, imageModel, videoModel, audioModel, imageModels, setShowInstallDialog, autoModelSelection } =
    useConfigs()
  const [prompt, setPrompt] = useState('')
  const textareaRef = useRef<TextAreaRef>(null)
  const [images, setImages] = useState<
    {
      file_id: string
      width: number
      height: number
    }[]
  >([])
  const [isFocused, setIsFocused] = useState(false)

  const [selectedModelType, setSelectedModelType] = useState<string>('')
  const imageInputRef = useRef<HTMLInputElement>(null)
  const [videos, setVideos] = useState<{ file_id: string }[]>([])
  const videoInputRef = useRef<HTMLInputElement>(null)
  
  const [audios, setAudios] = useState<{ file_id: string }[]>([])
  const audioInputRef = useRef<HTMLInputElement>(null)

  const { mutate: uploadImageMutation } = useMutation({
    mutationFn: (file: File) => uploadImage(file),
    onSuccess: (data) => {
      console.log('🦄uploadImageMutation onSuccess', data)
      setImages((prev) => [
        ...prev,
        {
          file_id: data.file_id,
          width: data.width,
          height: data.height,
        },
      ])
    },
  })
  const { mutate: uploadAudioMutation } = useMutation({
    mutationFn: (file: File) => uploadAudio(file),
    onSuccess: (data) => {
      console.log('🎵 uploadAudioMutation onSuccess', data)
      setAudios((prev) => [...prev, { file_id: data.file_id }])
      toast.success('音频上传成功')
    },
  })

  const handleAudioUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files) {
        for (const file of files) {
          uploadAudioMutation(file)
        }
      }
    },
    [uploadAudioMutation]
  )

  const { mutate: uploadVideoMutation } = useMutation({
    mutationFn: (file: File) => uploadVideo(file),
    onSuccess: (data) => {
      console.log('🎬 uploadVideoMutation onSuccess', data)
      setVideos((prev) => [...prev, { file_id: data.file_id }])
      toast.success('视频上传成功')
   },
  })

  const handleImagesUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files) {
        for (const file of files) {
          uploadImageMutation(file)
        }
      }
    },
    [uploadImageMutation]
  )

  const handleVideosUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files) {
        for (const file of files) {
          uploadVideoMutation(file)
        }
      }
    },
    [uploadVideoMutation]
  )
  const handleCancelChat = useCallback(async () => {
    if (sessionId) {
      await cancelChat(sessionId)
    }
    onCancelChat?.()
  }, [sessionId, onCancelChat])

  // Send Prompt
  const handleSendPrompt = useCallback(() => {
    if (pending) return
    if (!textModel) {
      toast.error(t('chat:textarea.selectModel'))
      return
    }
    // Check if there are image models, if not, prompt to install ComfyUI
    // if (!imageModel || imageModels.length === 0) {
    //   setShowInstallDialog(true)
    //   return
    // }
    let value = prompt
    if (value.length === 0 || value.trim() === '') {
      toast.error(t('chat:textarea.enterPrompt'))
      return
    }

    if (images.length > 0) {
      images.forEach((image) => {
        value += `\n\n ![Attached image - width: ${image.width} height: ${image.height} filename: ${image.file_id}](/api/file/${image.file_id})`
      })
    }
    if (videos.length > 0) {
      videos.forEach((video) => {
      value += `\n\n [Attached video filename: ${video.file_id}](/api/file/${video.file_id})`
      })
    }
    if (audios.length > 0) {
      audios.forEach((audio) => {
        value += `\n\n [Attached audio filename: ${audio.file_id}](/api/file/${audio.file_id})`
      })
    }
    const newMessage = messages.concat([
      {
        role: 'user',
        content: value,
      },
    ])
    setImages([])
    setVideos([])
    setAudios([])
    setPrompt('')
   
    onSendMessages(newMessage, {
      textModel: textModel,
      imageModel: imageModel || {
        provider: '',
        model: '',
        url: '',
      },
      videoModel: videoModel,
      autoModelSelection: autoModelSelection,
    })
  }, [
    pending,
    textModel,
    imageModel,
    imageModels,
    prompt,
    onSendMessages,
    images,
    messages,
    t,
  ])

  // Drop Area
  const dropAreaRef = useRef<HTMLDivElement>(null)
  const [isDragOver, setIsDragOver] = useState(false)

  const handleFilesDrop = useCallback(
    (files: File[]) => {
      for (const file of files) {
        uploadImageMutation(file)
      }
    },
    [uploadImageMutation]
  )

  useDrop(dropAreaRef, {
    onDragOver() {
      setIsDragOver(true)
    },
    onDragLeave() {
      setIsDragOver(false)
    },
    onDrop() {
      setIsDragOver(false)
    },
    onFiles: handleFilesDrop,
  })

  useEffect(() => {
    const handleAddImagesToChat = (data: TCanvasAddImagesToChatEvent) => {
      data.forEach(async (image) => {
        if (image.base64) {
          const file = dataURLToFile(image.base64, image.fileId)
          uploadImageMutation(file)
        } else {
          setImages(
            produce((prev) => {
              prev.push({
                file_id: image.fileId,
                width: image.width,
                height: image.height,
              })
            })
          )
        }
      })

      textareaRef.current?.focus()
    }
    eventBus.on('Canvas::AddImagesToChat', handleAddImagesToChat)
    return () => {
      eventBus.off('Canvas::AddImagesToChat', handleAddImagesToChat)
    }
  }, [uploadImageMutation])

  useEffect(() => {
    if (imageModel?.model) {
      const modelName = imageModel.model.toLowerCase()
      if (modelName.includes('kontext')) setSelectedModelType('image-edit')
      else if (modelName.includes('multi')) setSelectedModelType('multi-image')
      else if (modelName.includes('image-upscale')) setSelectedModelType('image-upscale')
      else setSelectedModelType('text-to-image')
    }
    if (videoModel?.model) {
      const modelName = videoModel.model.toLowerCase()
      if (modelName.includes('i2v')) setSelectedModelType('image-to-video')
      else if (modelName.includes('t2v')) setSelectedModelType('text-to-video')
      else if (modelName.includes('db-model')) setSelectedModelType('add-audio')
      else if (modelName.includes('s2v')) setSelectedModelType('image-audio')
    }
    if (audioModel?.model) {  // 新增
      const modelName = audioModel.model.toLowerCase()
      if (modelName.includes('t2a')) setSelectedModelType('text-to-audio')
    }
  }, [imageModel, videoModel])

  return (
    <motion.div
      ref={dropAreaRef}
      className={cn(
        'w-full flex flex-col items-center border border-primary/20 rounded-2xl p-3 hover:border-primary/40 transition-all duration-300 cursor-text gap-5 bg-background/80 backdrop-blur-xl relative',
        isFocused && 'border-primary/40',
        className
      )}
      style={{
        boxShadow: isFocused
          ? '0 0 0 4px color-mix(in oklab, var(--primary) 10%, transparent)'
          : 'none',
      }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3, ease: 'linear' }}
      onClick={() => textareaRef.current?.focus()}
    >
      <AnimatePresence>
        {isDragOver && (
          <motion.div
            className="absolute top-0 left-0 right-0 bottom-0 bg-background/50 backdrop-blur-xl rounded-2xl z-10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
          >
            <div className="flex items-center justify-center h-full">
              <p className="text-sm text-muted-foreground">
                Drop images here to upload
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {images.length > 0 && (
          <motion.div
            className="flex items-center gap-2 w-full"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
          >
            {images.map((image) => (
              <motion.div
                key={image.file_id}
                className="relative size-10"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2, ease: 'easeInOut' }}
              >
                <img
                  key={image.file_id}
                  src={`/api/file/${image.file_id}`}
                  alt="Uploaded image"
                  className="w-full h-full object-cover rounded-md"
                  draggable={false}
                />
                <Button
                  variant="secondary"
                  size="icon"
                  className="absolute -top-1 -right-1 size-4"
                  onClick={() =>
                    setImages((prev) =>
                      prev.filter((i) => i.file_id !== image.file_id)
                    )
                  }
                >
                  <XIcon className="size-3" />
                </Button>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {videos.length > 0 && (
          <motion.div
            className="flex items-center gap-2 w-full"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
          >
            {videos.map((video) => (
              <motion.div
                key={video.file_id}
                className="relative size-10"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2, ease: 'easeInOut' }}
              >
                <video
                  src={`/api/file/${video.file_id}`}
                  className="w-full h-full object-cover rounded-md"
                />
                <Button
                  variant="secondary"
                  size="icon"
                  className="absolute -top-1 -right-1 size-4"
                  onClick={() =>
                    setVideos((prev) =>
                      prev.filter((v) => v.file_id !== video.file_id)
                    )
                  }
                >
                  <XIcon className="size-3" />
                </Button>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {audios.length > 0 && (
          <motion.div
            className="flex items-center gap-2 w-full"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
          >
            {audios.map((audio) => (
              <motion.div
                key={audio.file_id}
                className="relative size-10"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2, ease: 'easeInOut' }}
              >
                <audio src={`/api/file/${audio.file_id}`} className="w-full h-full" controls />
                <Button
                  variant="secondary"
                  size="icon"
                  className="absolute -top-1 -right-1 size-4"
                  onClick={() => setAudios((prev) => prev.filter((a) => a.file_id !== audio.file_id))}
                >
                  <XIcon className="size-3" />
                </Button>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <Textarea
        ref={textareaRef}
        className="w-full h-full border-none outline-none resize-none max-h-[calc(100vh-700px)]"
        placeholder={t('chat:textarea.placeholder')}
        value={prompt}
        autoSize
        onChange={(e) => setPrompt(e.target.value)}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendPrompt()
          }
        }}
      />

      <div className="flex items-center justify-between gap-2 w-full">
        <div className="flex items-center gap-2 max-w-[calc(100%-50px)]">
          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={handleImagesUpload}
            hidden
          />
          <input
            ref={audioInputRef}
            type="file"
            accept="audio/*"
            onChange={handleAudioUpload}
            hidden
          />
          <input
            ref={videoInputRef}
            type="file"
            accept="video/*"
            onChange={handleVideosUpload}
            hidden
          />

          {/* 图片按钮 - 图像编辑、多图生成、图片高清放大、图生视频时显示 */}
          {['image-edit', 'image-audio', 'multi-image', 'image-upscale', 'image-to-video'].includes(selectedModelType) && (
            <Button
              variant="outline"
              size="icon"
              onClick={() => imageInputRef.current?.click()}
            >
              <Image className="size-4" />
            </Button>
          )}

          {/* 视频按钮 - 添加音频时显示 */}
          {selectedModelType === 'add-audio' && (
            <Button
              variant="outline"
              size="icon"
              onClick={() => videoInputRef.current?.click()}
              title="上传视频"
            >
              <Video className="size-4" />
            </Button>
          )}

          {/* 音频按钮 - 添加音频时显示 */}
          {['add-audio','text-to-audio', 'image-audio'].includes(selectedModelType) && (
            <Button
              variant="outline"
              size="icon"
              onClick={() => audioInputRef.current?.click()}
              title="上传音频"
            >
              <Music className="size-4" />
            </Button>
          )}

          <ModelSelector />
        </div>

        {pending ? (
          <Button
            className="shrink-0 relative"
            variant="default"
            size="icon"
            onClick={handleCancelChat}
          >
            <Loader2 className="size-5.5 animate-spin absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
            <Square className="size-2 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </Button>
        ) : (
          <Button
            className="shrink-0"
            variant="default"
            size="icon"
            onClick={handleSendPrompt}
            disabled={!textModel || !imageModel || prompt.length === 0}
          >
            <ArrowUp className="size-4" />
          </Button>
        )}
      </div>
    </motion.div>
  )
}

export default ChatTextarea

