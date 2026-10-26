// Máscara do sujeito de uma foto, local e de graça (Vision do macOS).
//   swift recorte.swift <imagem> <mascara.png> [objeto|pessoa]
// objeto: VNGenerateForegroundInstanceMaskRequest (qualquer sujeito em primeiro plano, macOS 14+)
// pessoa: VNGeneratePersonSegmentationRequest (só gente, cabelo melhor)
// A máscara sai em tons de cinza, do tamanho da imagem (255 = sujeito).
import Foundation
import Vision
import CoreImage
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count >= 3 else {
    print("uso: swift recorte.swift <imagem> <mascara.png> [objeto|pessoa]")
    exit(1)
}
let entrada = URL(fileURLWithPath: args[1])
let saida = URL(fileURLWithPath: args[2])
let modo = args.count > 3 ? args[3] : "objeto"

guard let fonte = CGImageSourceCreateWithURL(entrada as CFURL, nil),
      let cg = CGImageSourceCreateImageAtIndex(fonte, 0, nil) else {
    print("não consegui abrir \(entrada.path)")
    exit(1)
}
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
var mascara: CVPixelBuffer? = nil
do {
    if modo == "pessoa" {
        let req = VNGeneratePersonSegmentationRequest()
        req.qualityLevel = .accurate
        req.outputPixelFormat = kCVPixelFormatType_OneComponent8
        try handler.perform([req])
        mascara = req.results?.first?.pixelBuffer
    } else {
        let req = VNGenerateForegroundInstanceMaskRequest()
        try handler.perform([req])
        if let obs = req.results?.first {
            mascara = try obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: handler)
        }
    }
} catch {
    print("Vision falhou: \(error)")
    exit(2)
}
guard let buf = mascara else {
    print("nenhum sujeito encontrado")
    exit(2)
}
var ci = CIImage(cvPixelBuffer: buf)
let sx = CGFloat(cg.width) / ci.extent.width
let sy = CGFloat(cg.height) / ci.extent.height
ci = ci.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
let ctx = CIContext()
guard let out = ctx.createCGImage(ci, from: CGRect(x: 0, y: 0, width: cg.width, height: cg.height),
                                  format: .L8, colorSpace: CGColorSpaceCreateDeviceGray()) else {
    print("não consegui gerar a máscara")
    exit(3)
}
guard let destino = CGImageDestinationCreateWithURL(saida as CFURL, UTType.png.identifier as CFString, 1, nil) else {
    print("não consegui gravar \(saida.path)")
    exit(3)
}
CGImageDestinationAddImage(destino, out, nil)
CGImageDestinationFinalize(destino)
print("ok \(cg.width)x\(cg.height) \(modo)")
