// Recorte local do sujeito (Vision, só macOS 14+): swift recorte.swift entrada.jpg saida.png
// Em outro sistema, recorte no Higgsfield (remover fundo) ou com outra ferramenta de recorte com alfa.
// Gera PNG com alfa só do(s) sujeito(s) em primeiro plano. Sem rede, sem crédito.
import Foundation
import Vision
import CoreImage
import AppKit

let args = CommandLine.arguments
guard args.count >= 3 else { print("uso: recorte.swift entrada saida.png"); exit(1) }
let url = URL(fileURLWithPath: args[1])
guard let ci = CIImage(contentsOf: url) else { print("erro: não li \(args[1])"); exit(2) }
let req = VNGenerateForegroundInstanceMaskRequest()
let handler = VNImageRequestHandler(ciImage: ci, options: [:])
do { try handler.perform([req]) } catch { print("erro: \(error)"); exit(3) }
guard let obs = req.results?.first else { print("erro: nenhum sujeito"); exit(4) }
let buf = try obs.generateMaskedImage(ofInstances: obs.allInstances, from: handler, croppedToInstancesExtent: false)
let out = CIImage(cvPixelBuffer: buf)
let ctx = CIContext()
try ctx.writePNGRepresentation(of: out, to: URL(fileURLWithPath: args[2]), format: .RGBA8, colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!)
print("ok \(obs.allInstances.count) sujeito(s)")
