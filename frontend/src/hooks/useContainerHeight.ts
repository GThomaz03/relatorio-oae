import { useEffect, useState, type RefObject } from 'react'

/** Mede altura disponível de um container via ResizeObserver (estável em resize de janela). */
export function useContainerHeight(
  ref: RefObject<HTMLElement | null>,
  min = 200,
): number {
  const [height, setHeight] = useState(min)

  useEffect(() => {
    const element = ref.current
    if (!element) return

    const update = () => {
      setHeight(Math.max(min, element.clientHeight))
    }

    update()
    const observer = new ResizeObserver(update)
    observer.observe(element)
    return () => observer.disconnect()
  }, [ref, min])

  return height
}
